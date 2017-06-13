##
# See the file COPYRIGHT for copyright information.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
##

"""
Incident Management System SQLite data store.
"""

from datetime import (
    datetime as DateTime, timedelta as TimeDelta, timezone as TimeZone
)
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, Iterable, Optional, Tuple
from typing.io import TextIO

from attr import Factory, attrib, attrs
from attr.validators import instance_of, optional

from twisted.logger import Logger

from ims.ext.sqlite import (
    Connection, Cursor, Parameters, SQLiteError, createDB, openDB, printSchema
)
from ims.model import (
    Event, Incident, IncidentPriority, IncidentState, Location, Ranger,
    ReportEntry, RodGarettAddress,
)

from .._abc import IMSDataStore
from .._exceptions import StorageError

Parameters  # Silence linter


__all__ = ()


def _query(query: str) -> str:
    return dedent(query.format(
        query_eventID="select ID from EVENT where NAME = :eventID",
    ))



@attrs(frozen=True)
class DataStore(IMSDataStore):
    """
    Incident Management System SQLite data store.
    """

    _log = Logger()
    _schema = None

    @attrs(frozen=False)
    class _State(object):
        """
        Internal mutable state for :class:`Connection`.
        """

        db = attrib(
            validator=optional(instance_of(Connection)),
            default=None, init=False,
        )

    dbPath = attrib(validator=instance_of(Path))           # type: Path
    _state = attrib(default=Factory(_State), init=False)  # type: _State


    @classmethod
    def _loadSchema(cls) -> str:
        if cls._schema is None:
            path = Path(__file__).parent / "schema.sqlite"
            schema = path.read_text()
            cls._schema = schema
        return cls._schema


    @classmethod
    def printSchema(cls, out: TextIO) -> None:
        """
        Print schema.
        """
        with createDB(None, cls._loadSchema()) as db:
            printSchema(db, out=out)


    @property
    def _db(self) -> Connection:
        if self._state.db is None:
            try:
                db = openDB(self.dbPath, schema=self._loadSchema())
            except SQLiteError as e:
                raise StorageError(e)
            self._state.db = db

        return self._state.db


    def _execute(
        self, queries: Iterable[Tuple[str, Dict[str, Any]]],
        errorLogFormat: str,
    ) -> None:
        try:
            with self._db as db:
                for (query, queryArgs) in queries:
                    db.execute(query, queryArgs)
        except SQLiteError as e:
            self._log.critical(
                errorLogFormat, query=query, **queryArgs, error=e
            )
            raise StorageError(e)


    def _executeAndIterate(
        self, query: str, queryArgs: Dict[str, Any], errorLogFormat: str
    ) -> Iterable[Any]:
        try:
            for row in self._db.execute(query, queryArgs):
                yield row
        except SQLiteError as e:
            self._log.critical(
                errorLogFormat, query=query, **queryArgs, error=e
            )
            raise StorageError(e)


    async def events(self) -> Iterable[Event]:
        """
        Look up all events in this store.
        """
        return (
            Event(row["name"]) for row in self._executeAndIterate(
                self._query_events, {}, "Unable to look up events"
            )
        )

    _query_events = _query(
        """
        select NAME from EVENT
        """
    )


    async def createEvent(self, event: Event) -> None:
        """
        Create an event with the given name.
        """
        self._execute(
            (
                (self._query_createEvent, dict(eventID=event.id)),
            ),
            "Unable to create event: {eventID}"
        )

    _query_createEvent = _query(
        """
        insert into EVENT (NAME) values (:eventID);
        """
    )


    async def incidentTypes(
        self, includeHidden: bool = False
    ) -> Iterable[str]:
        """
        Look up the incident types used in this store.
        """
        if includeHidden:
            query = self._query_incidentTypes
        else:
            query = self._query_incidentTypesNotHidden

        return (
            row["name"] for row in self._executeAndIterate(
                query, {}, "Unable to look up incident types"
            )
        )

    _query_incidentTypes = _query(
        """
        select NAME from INCIDENT_TYPE
        """
    )

    _query_incidentTypesNotHidden = _query(
        """
        select NAME from INCIDENT_TYPE where HIDDEN = 0
        """
    )


    async def createIncidentType(
        self, incidentType: str, hidden: bool = False
    ) -> None:
        """
        Create the given incident type.
        """
        self._execute(
            (
                (
                    self._query_createIncidentType,
                    dict(incidentType=incidentType, hidden=hidden),
                ),
            ),
            "Unable to create incident type: {name}"
        )

    _query_createIncidentType = _query(
        """
        insert into INCIDENT_TYPE (NAME, HIDDEN)
        values (:incidentType, :hidden)
        """
    )


    def _hideShowIncidentTypes(
        self, incidentTypes: Iterable[str], hidden: bool
    ) -> None:
        if hidden:
            action = "hide"
        else:
            action = "show"

        self._execute(
            (
                (
                    self._query_hideShowIncidentType,
                    dict(incidentType=incidentType, hidden=hidden),
                )
                for incidentType in incidentTypes
            ),
            "Unable to {} incident types: {{incidentTypes}}".format(action)
        )

    _query_hideShowIncidentType = _query(
        """
        update INCIDENT_TYPE set HIDDEN = :hidden where NAME = :incidentType
        """
    )


    async def showIncidentTypes(self, incidentTypes: Iterable[str]) -> None:
        """
        Show the given incident types.
        """
        return self._hideShowIncidentTypes(incidentTypes, False)


    async def hideIncidentTypes(self, incidentTypes: Iterable[str]) -> None:
        """
        Hide the given incident types.
        """
        return self._hideShowIncidentTypes(incidentTypes, True)


    def _fetchIncident(
        self, event: Event, number: int, cursor: Cursor
    ) -> Incident:
        params: Parameters = dict(
            eventID=event.id, incidentNumber=number
        )

        cursor.execute(self._query_incident, params)
        row = cursor.fetchone()

        rangerHandles = tuple(
            row["RANGER_HANDLE"]
            for row in cursor.execute(self._query_incident_rangers, params)
        )

        incidentTypes = tuple(
            row["NAME"]
            for row in cursor.execute(self._query_incident_types, params)
        )

        reportEntries = tuple(
            ReportEntry(
                created=fromTimeStamp(row["CREATED"]),
                author=row["AUTHOR"],
                automatic=bool(row["GENERATED"]),
                text=row["TEXT"],
            )
            for row in self._db.execute(
                self._query_incident_reportEntries, params
            )
        )

        return Incident(
            event=event,
            number=number,
            created=fromTimeStamp(row["CREATED"]),
            state=incidentStateFromID(row["STATE"]),
            priority=priorityFromInteger(row["PRIORITY"]),
            summary=row["SUMMARY"],
            location=Location(
                name=row["LOCATION_NAME"],
                address=RodGarettAddress(
                    concentric=row["LOCATION_CONCENTRIC"],
                    radialHour=row["LOCATION_RADIAL_HOUR"],
                    radialMinute=row["LOCATION_RADIAL_MINUTE"],
                    description=row["LOCATION_DESCRIPTION"],
                ),
            ),
            rangerHandles=rangerHandles,
            incidentTypes=incidentTypes,
            reportEntries=reportEntries,
        )

    _query_incident = _query(
        """
        select
            CREATED, PRIORITY, STATE, SUMMARY,
            LOCATION_NAME,
            LOCATION_CONCENTRIC,
            LOCATION_RADIAL_HOUR,
            LOCATION_RADIAL_MINUTE,
            LOCATION_DESCRIPTION
        from INCIDENT i
        where EVENT = ({query_eventID}) and NUMBER = :incidentNumber
        """
    )

    _query_incident_rangers = _query(
        """
        select RANGER_HANDLE from INCIDENT__RANGER
        where EVENT = ({query_eventID}) and INCIDENT_NUMBER = :incidentNumber
        """
    )

    _query_incident_types = _query(
        """
        select NAME from INCIDENT_TYPE where ID in (
            select INCIDENT_TYPE from INCIDENT__INCIDENT_TYPE
            where
                EVENT = ({query_eventID}) and
                INCIDENT_NUMBER = :incidentNumber
        )
        """
    )

    _query_incident_reportEntries = _query(
        """
        select AUTHOR, TEXT, CREATED, GENERATED from REPORT_ENTRY
        where ID in (
            select REPORT_ENTRY from INCIDENT__REPORT_ENTRY
            where
                EVENT = ({query_eventID}) and
                INCIDENT_NUMBER = :incidentNumber
        )
        """
    )


    def _fetchIncidentNumbers(
        self, event: Event, cursor: Cursor
    ) -> Iterable[int]:
        """
        Look up all incident numbers for the given event.
        """
        for row in cursor.execute(
            self._query_incidentNumbers, dict(eventID=event.id)
        ):
            yield row["NUMBER"]

    _query_incidentNumbers = _query(
        """
        select NUMBER from INCIDENT where EVENT = ({query_eventID})
        """
    )


    async def incidents(self, event: Event) -> Iterable[Incident]:
        """
        Look up all incidents for the given event.
        """
        try:
            with self._db as db:
                cursor = db.cursor()
                try:
                    # FIXME: This should be an async generator
                    return tuple(
                        self._fetchIncident(event, number, cursor)
                        for number in self._fetchIncidentNumbers(event, cursor)
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self._log.critical(
                "Unable to look up incident #{number} in {event}",
                event=event, number=number, error=e,
            )
            raise StorageError(e)


    async def incidentWithNumber(self, event: Event, number: int) -> Incident:
        """
        Look up the incident with the given number in the given event.
        """
        try:
            with self._db as db:
                cursor = db.cursor()
                try:
                    return self._fetchIncident(event, number, cursor)
                finally:
                    cursor.close()
        except SQLiteError as e:
            self._log.critical(
                "Unable to look up incident #{number} in {event}",
                event=event, number=number, error=e,
            )
            raise StorageError(e)


    def _nextIncidentNumber(self, event: Event, cursor: Cursor) -> int:
        """
        Look up the next available incident number.
        """
        cursor.execute(self._query_maxIncidentNumber, dict(eventID=event.id))
        number = cursor.fetchone().get("NUMBER", None)
        if number is None:
            return 1
        else:
            return number + 1

    _query_maxIncidentNumber = _query(
        """
        select max(NUMBER) from INCIDENT where EVENT = ({query_eventID})
        """
    )


    async def _createIncident(
        self, incident: Incident, author: Optional[Ranger],
        directImport: bool,
    ) -> None:
        """
        Create a new incident and add it into the given event.
        The incident number is determined by the database; the given incident
        must have an incident number value of zero.
        """
        try:
            with self._db as db:
                cursor = db.cursor()
                try:
                    # Replace incident number with a new one (unless we are
                    # importing).
                    if not directImport:
                        assert incident.number == 0, (
                            "New incident number must be zero"
                        )
                        number = self._nextIncidentNumber(
                            incident.event, cursor
                        )
                        incident = incident.replace(number=number)

                    # Get normalized-to-Rod-Garett address fields
                    location = incident.location
                    address = location.address

                    if isinstance(address, RodGarettAddress):
                        locationConcentric   = address.concentric
                        locationRadialHour   = address.radialHour
                        locationRadialMinute = address.radialMinute
                    else:
                        locationConcentric   = None
                        locationRadialHour   = None
                        locationRadialMinute = None

                    # Write incident row
                    cursor.execute(
                        self._query_createIncident, dict(
                            eventID=incident.event.id,
                            incidentNumber=incident.number,
                            incidentCreated=asTimeStamp(incident.created),
                            incidentPriority=incident.priority,
                            incidentState=incidentStateAsID(incident.state),
                            incidentSummary=incident.summary,
                            locationName=location.name,
                            locationConcentric=locationConcentric,
                            locationRadialHour=locationRadialHour,
                            locationRadialMinute=locationRadialMinute,
                            locationDescription=address.description,
                        )
                    )

                    # Join with Ranger handles

                    # Join with incident types

                    if not directImport:
                        # Add initial report entry
                        pass

                    # Add report entries
                finally:
                    cursor.close()
        except SQLiteError as e:
            self._log.critical(
                "Unable to create incident {incident}",
                incident=incident, author=author, error=e,
            )
            raise StorageError(e)

    _query_createIncident = _query(
        """
        insert into INCIDENT (
            EVENT,
            NUMBER,
            VERSION,
            CREATED,
            PRIORITY,
            STATE,
            SUMMARY,
            LOCATION_NAME,
            LOCATION_CONCENTRIC,
            LOCATION_RADIAL_HOUR,
            LOCATION_RADIAL_MINUTE,
            LOCATION_DESCRIPTION
        )
        values (
            ({query_eventID}),
            :incidentNumber,
            1,
            :incidentCreated,
            :incidentPriority,
            :incidentState,
            :incidentSummary,
            :locationName,
            :locationConcentric,
            :locationRadialHour,
            :locationRadialMinute,
            :locationDescription
        )
        """
    )


    async def createIncident(
        self, incident: Incident, author: Ranger
    ) -> None:
        """
        Create a new incident and add it into the given event.
        The incident number is determined by the database; the given incident
        must have an incident number value of zero.
        """
        self._createIncident(incident, author, False)


    async def importIncident(self, incident: Incident) -> None:
        """
        Import an incident and add it into the given event.
        """
        self._createIncident(incident, None, True)



zeroTimeDelta = TimeDelta(0)


def asTimeStamp(dateTime: DateTime) -> float:
    assert dateTime.tzinfo is not None, repr(dateTime)
    return dateTime.timestamp()


def fromTimeStamp(timeStamp: float) -> DateTime:
    return DateTime.fromtimestamp(timeStamp, tz=TimeZone.utc)


def incidentStateFromID(strValue: str) -> IncidentState:
    return {
        "new":        IncidentState.new,
        "on_hold":    IncidentState.onHold,
        "dispatched": IncidentState.dispatched,
        "on_scene":   IncidentState.onScene,
        "closed":     IncidentState.closed,
    }[strValue]


def incidentStateAsID(incidentState: IncidentState) -> str:
    return {
        IncidentState.new:        "new",
        IncidentState.onHold:     "on_hold",
        IncidentState.dispatched: "dispatched",
        IncidentState.onScene:    "on_scene",
        IncidentState.closed:     "closed",
    }[incidentState]


def priorityFromInteger(intValue: int) -> IncidentPriority:
    return {
        1: IncidentPriority.high,
        2: IncidentPriority.high,
        3: IncidentPriority.normal,
        4: IncidentPriority.low,
        5: IncidentPriority.low,
    }[intValue]


def priorityAsInteger(priority: IncidentPriority) -> int:
    return {
        IncidentPriority.high:   1,
        IncidentPriority.normal: 3,
        IncidentPriority.low:    4,
    }[priority]
