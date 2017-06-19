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
from types import MappingProxyType
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple, cast
from typing.io import TextIO

from attr import Factory, attrib, attrs
from attr.validators import instance_of, optional

from twisted.logger import Logger

from ims.ext.sqlite import (
    Connection, Cursor, ParameterValue, Parameters, Row, SQLiteError,
    createDB, openDB, printSchema,
)
from ims.model import (
    Event, Incident, IncidentPriority, IncidentState, Location, ReportEntry,
    RodGarettAddress,
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
        self, queries: Iterable[Tuple[str, Parameters]],
        errorLogFormat: str,
    ) -> None:
        try:
            with self._db as db:
                for (query, parameters) in queries:
                    db.execute(query, parameters)
        except SQLiteError as e:
            self._log.critical(
                errorLogFormat, query=query, **parameters, error=e
            )
            raise StorageError(e)


    def _executeAndIterate(
        self, query: str, parameters: Parameters, errorLogFormat: str
    ) -> Iterable[Row]:
        try:
            for row in self._db.execute(query, parameters):
                yield row
        except SQLiteError as e:
            self._log.critical(
                errorLogFormat, query=query, **parameters, error=e
            )
            raise StorageError(e)


    async def events(self) -> Iterable[Event]:
        """
        See :meth:`IMSDataStore.events`.
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
        See :meth:`IMSDataStore.createEvent`.
        """
        self._log.info("Creating event: {event}", event=event)

        self._execute(
            (
                (self._query_createEvent, dict(eventID=event.id)),
            ),
            "Unable to create event {eventID}"
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
        See :meth:`IMSDataStore.incidentTypes`.
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
        See :meth:`IMSDataStore.createIncidentType`.
        """
        self._log.info(
            "Creating incident type: {incidentType} (hidden={hidden})",
            incidentType=incidentType, hidden=hidden,
        )

        self._execute(
            ((
                # FIXME: This casting shouldn't be necessary
                cast(str, self._query_createIncidentType),
                cast(
                    Dict[str, ParameterValue],
                    dict(incidentType=incidentType, hidden=hidden)
                ),
            ),),
            "Unable to create incident type {name}"
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
        self._log.info(
            "Setting hidden to {hidden} for incident types: {incidentTypes}",
            incidentTypes=incidentTypes, hidden=hidden,
        )

        self._execute(
            (
                (
                    self._query_hideShowIncidentType,
                    dict(incidentType=incidentType, hidden=hidden),
                )
                for incidentType in incidentTypes
            ),
            "Unable to set hidden to {hidden} incident types {{incidentTypes}}"
            .format(hidden=hidden)
        )

    _query_hideShowIncidentType = _query(
        """
        update INCIDENT_TYPE set HIDDEN = :hidden where NAME = :incidentType
        """
    )


    async def showIncidentTypes(self, incidentTypes: Iterable[str]) -> None:
        """
        See :meth:`IMSDataStore.showIncidentTypes`.
        """
        return self._hideShowIncidentTypes(incidentTypes, False)


    async def hideIncidentTypes(self, incidentTypes: Iterable[str]) -> None:
        """
        See :meth:`IMSDataStore.hideIncidentTypes`.
        """
        return self._hideShowIncidentTypes(incidentTypes, True)


    async def concentricStreets(self, event: Event) -> Mapping[str, str]:
        """
        See :meth:`IMSDataStore.concentricStreets`.
        """
        return MappingProxyType(dict(
            (row["ID"], row["NAME"]) for row in
            self._executeAndIterate(
                self._query_concentricStreets, dict(eventID=event.id),
                "Unable to look up concentric streets for event {event}"
            )
        ))


    _query_concentricStreets = _query(
        """
        select ID, NAME from CONCENTRIC_STREET where EVENT = ({query_eventID})
        """
    )


    async def createConcentricStreet(
        self, event: Event, id: str, name: str
    ) -> None:
        """
        See :meth:`IMSDataStore.createConcentricStreet`.
        """
        self._log.info(
            "Creating concentric street in event {event}: ({id}){name}",
            event=event, id=id, name=name,
        )

        self._execute(
            ((
                self._query_createConcentricStreet,
                dict(eventID=event.id, streetID=id, streetName=name)
            ),),
            "Unable to create concentric street ({streetID}){streetName} "
            "for event {event}"
        )

    _query_createConcentricStreet = _query(
        """
        insert into CONCENTRIC_STREET (EVENT, ID, NAME)
        values (({query_eventID}), :streetID, :streetName)
        """
    )


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
            for row in cursor.execute(
                self._query_incident_reportEntries, params
            )
        )

        # FIXME: This is because schema thinks concentric is an int
        if row["LOCATION_CONCENTRIC"] is None:
            concentric = None
        else:
            concentric = str(row["LOCATION_CONCENTRIC"])

        return Incident(
            event=event,
            number=number,
            created=fromTimeStamp(row["CREATED"]),
            state=incidentStateFromID(row["STATE"]),
            priority=priorityFromID(row["PRIORITY"]),
            summary=row["SUMMARY"],
            location=Location(
                name=row["LOCATION_NAME"],
                address=RodGarettAddress(
                    concentric=concentric,
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
        See :meth:`IMSDataStore.incidents`.
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
                "Unable to look up incidents in {event}",
                event=event, error=e,
            )
            raise StorageError(e)


    async def incidentWithNumber(self, event: Event, number: int) -> Incident:
        """
        See :meth:`IMSDataStore.incidentWithNumber`.
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


    def _attachRangeHandlesToIncident(
        self, event: Event, incidentNumber: int, rangerHandles: Iterable[str],
        cursor: Cursor,
    ) -> None:
        self._log.info(
            "Attaching Rangers to incident #{incidentNumber} in event "
            "{event}: {rangerHandles}",
            event=event,
            incidentNumber=incidentNumber,
            rangerHandles=rangerHandles,
        )

        for rangerHandle in rangerHandles:
            cursor.execute(
                self._query_attachRangeHandleToIncident, dict(
                    eventID=event.id,
                    incidentNumber=incidentNumber,
                    rangerHandle=rangerHandle,
                )
            )

    _query_attachRangeHandleToIncident = _query(
        """
        insert into INCIDENT__RANGER (EVENT, INCIDENT_NUMBER, RANGER_HANDLE)
        values (({query_eventID}), :incidentNumber, :rangerHandle)
        """
    )


    def _attachIncidentTypesToIncident(
        self, event: Event, incidentNumber: int, incidentTypes: Iterable[str],
        cursor: Cursor,
    ) -> None:
        self._log.info(
            "Attaching incident types to incident #{incidentNumber} in event: "
            "{event}: {incidentTypes}",
            event=event,
            incidentNumber=incidentNumber,
            incidentTypes=incidentTypes,
        )

        for incidentType in incidentTypes:
            cursor.execute(
                self._query_attachIncidentTypeToIncident, dict(
                    eventID=event.id,
                    incidentNumber=incidentNumber,
                    incidentType=incidentType,
                )
            )

    _query_attachIncidentTypeToIncident = _query(
        """
        insert into INCIDENT__INCIDENT_TYPE (
            EVENT, INCIDENT_NUMBER, INCIDENT_TYPE
        )
        values (
            ({query_eventID}),
            :incidentNumber,
            (select ID from INCIDENT_TYPE where NAME = :incidentType)
        )
        """
    )


    def _createReportEntry(
        self, reportEntry: ReportEntry, cursor: Cursor
    ) -> None:
        self._log.info(
            "Creating report entry: {reportEntry}", reportEntry=reportEntry
        )

        cursor.execute(
            self._query_addReportEntry, dict(
                created=asTimeStamp(reportEntry.created),
                generated=reportEntry.automatic,
                author=reportEntry.author,
                text=reportEntry.text,
            )
        )

    _query_addReportEntry = _query(
        """
        insert into REPORT_ENTRY (AUTHOR, TEXT, CREATED, GENERATED)
        values (:author, :text, :created, :generated)
        """
    )


    def _addAndAttachReportEntriesToIncident(
        self, event: Event, incidentNumber: int,
        reportEntries: Iterable[ReportEntry], cursor: Cursor,
    ) -> None:
        for reportEntry in reportEntries:
            self._createReportEntry(reportEntry, cursor)

            self._log.info(
                "Attaching report entry to incident #{incidentNumber} in "
                "event {event}: {reportEntry}",
                event=event,
                incidentNumber=incidentNumber,
                reportEntry=reportEntry,
            )

            # Join to incident
            cursor.execute(
                self._query_attachReportEntryToIncident, dict(
                    eventID=event.id,
                    incidentNumber=incidentNumber,
                    reportEntryID=cursor.lastrowid,
                )
            )

    _query_attachReportEntryToIncident = _query(
        """
        insert into INCIDENT__REPORT_ENTRY (
            EVENT, INCIDENT_NUMBER, REPORT_ENTRY
        )
        values (({query_eventID}), :incidentNumber, :reportEntryID)
        """
    )


    def _automaticReportEntry(
        self, author: str, created: DateTime, attribute: str, value: Any
    ) -> ReportEntry:
        return ReportEntry(
            text="Changed {} to: {}".format(attribute, value),
            author=author, created=created, automatic=True,
        )


    def _initialReportEntries(
        self, event: Event, incident: Incident, author: str
    ) -> Iterable[ReportEntry]:
        created = DateTime.now(TimeZone.utc)

        reportEntries = []

        def addEntry(attribute: str, value: Any) -> None:
            reportEntries.append(
                self._automaticReportEntry(
                    author, created, attribute, value
                )
            )

        if incident.priority != IncidentPriority.normal:
            addEntry("priority", incident.priority)

        if incident.state != IncidentState.new:
            addEntry("state", incident.state)

        if incident.summary:
            addEntry("summary", incident.summary)

        location = incident.location
        if location.name:
            addEntry("location name", location.name)

        address = location.address
        if address.description:
            addEntry("location description", address.description)

        if isinstance(address, RodGarettAddress):
            if address.concentric is not None:
                addEntry("location concentric street", address.concentric)
            if address.radialHour is not None:
                addEntry("location radial hour", address.radialHour)
            if address.radialMinute is not None:
                addEntry("location radial minute", address.radialMinute)

        if incident.rangerHandles:
            addEntry("Rangers", ", ".join(incident.rangerHandles))

        if incident.incidentTypes:
            addEntry("incident types", ", ".join(incident.incidentTypes))

        return tuple(reportEntries)


    async def _createIncident(
        self, incident: Incident, author: Optional[str],
        directImport: bool,
    ) -> Incident:
        if directImport:
            if author is not None:
                raise ValueError("author should be None for direct import")

            if not incident.number > 0:
                raise ValueError("Imported incident number must be > 0")
        else:
            if not author:
                raise ValueError("author is required")

            if incident.number != 0:
                raise ValueError("New incident number must be zero")

            for reportEntry in incident.reportEntries:
                if reportEntry.automatic:
                    raise ValueError(
                        "New incident may not contain automatic report entries"
                    )

            # Add initial report entries
            reportEntries = self._initialReportEntries(
                incident.event, incident, author
            )
            incident = incident.replace(
                reportEntries=(reportEntries + incident.reportEntries)
            )

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

        self._log.info("Creating incident: {incident}", incident=incident)

        try:
            with self._db as db:
                cursor = db.cursor()
                try:
                    if not directImport:
                        # Assign the incident number a number
                        number = self._nextIncidentNumber(
                            incident.event, cursor
                        )
                        incident = incident.replace(number=number)

                    # Write incident row
                    cursor.execute(
                        self._query_createIncident, dict(
                            eventID=incident.event.id,
                            incidentNumber=incident.number,
                            incidentCreated=asTimeStamp(incident.created),
                            incidentPriority=priorityAsID(incident.priority),
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
                    self._attachRangeHandlesToIncident(
                        incident.event, incident.number,
                        incident.rangerHandles, cursor,
                    )

                    # Attach incident types
                    self._attachIncidentTypesToIncident(
                        incident.event, incident.number,
                        incident.incidentTypes, cursor,
                    )

                    # Add report entries
                    self._addAndAttachReportEntriesToIncident(
                        incident.event, incident.number,
                        incident.reportEntries, cursor,
                    )

                    return incident
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
        self, incident: Incident, author: str
    ) -> Incident:
        """
        See :meth:`IMSDataStore.createIncident`.
        """
        return await self._createIncident(incident, author, False)


    async def importIncident(self, incident: Incident) -> None:
        """
        Import an incident and add it into the given event.
        """
        await self._createIncident(incident, None, True)



zeroTimeDelta = TimeDelta(0)


def asTimeStamp(dateTime: DateTime) -> float:
    assert dateTime.tzinfo is not None, repr(dateTime)
    timeStamp = dateTime.timestamp()
    if timeStamp < 0:
        raise StorageError(
            "DateTime is before the UTC epoch: {}".format(dateTime)
        )
    return timeStamp


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


def priorityFromID(intValue: int) -> IncidentPriority:
    return {
        1: IncidentPriority.high,
        2: IncidentPriority.high,
        3: IncidentPriority.normal,
        4: IncidentPriority.low,
        5: IncidentPriority.low,
    }[intValue]


def priorityAsID(priority: IncidentPriority) -> int:
    return {
        IncidentPriority.high:   1,
        IncidentPriority.normal: 3,
        IncidentPriority.low:    4,
    }[priority]
