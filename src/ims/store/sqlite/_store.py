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
from sys import stdout
from textwrap import dedent
from types import MappingProxyType
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple, Union, cast
from typing.io import TextIO

from attr import Factory, attrib, attrs
from attr.validators import instance_of, optional

from twisted.logger import Logger

from ims.ext.json import objectFromJSONBytesIO
from ims.ext.sqlite import (
    Connection, Cursor, ParameterValue, Parameters, Row, SQLiteError,
    createDB, explainQueryPlans, openDB, printSchema,
)
from ims.model import (
    Event, Incident, IncidentPriority, IncidentReport, IncidentState,
    Location, ReportEntry, RodGarettAddress,
)
from ims.model.json import IncidentJSONKey, modelObjectFromJSONObject

from .._db import DatabaseStore
from .._exceptions import (
    NoSuchIncidentError, NoSuchIncidentReportError, StorageError
)


__all__ = ()


def _query(query: str) -> str:
    return dedent(query.format(
        query_eventID="select ID from EVENT where NAME = :eventID",
    ))



@attrs(frozen=True)
class DataStore(DatabaseStore):
    """
    Incident Management System SQLite data store.
    """

    _log = Logger()

    schemaVersion = 2
    schemaBasePath = Path(__file__).parent / "schema"
    sqlFileExtension = "sqlite"


    @attrs(frozen=False)
    class _State(object):
        """
        Internal mutable state for :class:`DataStore`.
        """

        db: Optional[Connection] = attrib(
            validator=optional(instance_of(Connection)),
            default=None, init=False,
        )

    dbPath: Path = attrib(validator=instance_of(Path))
    _state: _State = attrib(default=Factory(_State), init=False)


    @classmethod
    def printSchema(cls, out: TextIO = stdout) -> None:
        """
        Print schema.
        """
        with createDB(None, cls.loadSchema()) as db:
            version = cls._dbSchemaVersion(db)
            print(f"Version: {version}", file=out)
            printSchema(db, out=out)


    @classmethod
    def printQueries(cls, out: TextIO = stdout) -> None:
        """
        Print a summary of queries.
        """
        queries = [
            (getattr(cls, k), k[7:])
            for k in sorted(vars(cls))
            if k.startswith("_query_")
        ]

        with createDB(None, cls.loadSchema()) as db:
            for line in explainQueryPlans(db, queries):
                print(line, file=out)
                print(file=out)


    @classmethod
    def _dbSchemaVersion(cls, db: Connection) -> int:
        try:
            rows = db.execute("select VERSION from SCHEMA_INFO")
            row = next(rows, None)
            if row is None:
                raise StorageError("Invalid schema: no version")
            return row["VERSION"]
        except SQLiteError as e:
            cls._log.critical(
                "Unable to look up schema version: {error}", error=e
            )
            raise StorageError(f"Unable to look up schema version: {e}")


    @property
    def _db(self) -> Connection:
        if self._state.db is None:
            try:
                self._state.db = openDB(self.dbPath, schema=self.loadSchema())

            except SQLiteError as e:
                self._log.critical(
                    "Unable to open SQLite database {dbPath}: {error}",
                    dbPath=self.dbPath, error=e,
                )
                raise StorageError(
                    f"Unable to open SQLite database {self.dbPath}: {e}"
                )

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
                errorLogFormat, queries=queries, error=e
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


    async def reconnect(self) -> None:
        """
        See :meth:`DatabaseStore.reconnect`.
        """
        self._state.db = None


    async def dbSchemaVersion(self) -> int:
        """
        See :meth:`DatabaseStore.dbSchemaVersion`.
        """
        return self._dbSchemaVersion(self._db)


    async def applySchema(self, sql: str) -> None:
        """
        See :meth:`IMSDataStore.applySchema`.
        """
        self._db.executescript(sql)
        self._db.validateConstraints()
        self._db.commit()


    async def validate(self) -> None:
        """
        See :meth:`IMSDataStore.validate`.
        """
        self._log.info("Validating data store...")

        valid = True

        try:
            self._db.validateConstraints()
        except SQLiteError as e:
            self._log.error(
                "Database constraint violated: {error}",
                error=e,
            )

        # Check for detached report entries
        for reportEntry in self.detachedReportEntries():
            self._log.error(
                "Found detached report entry: {reportEntry}",
                reportEntry=reportEntry,
            )
            valid = False

        if not valid:
            raise StorageError("Data store validation failed")


    def loadFromEventJSON(
        self, event: Event, path: Path, trialRun: bool = False
    ) -> None:
        """
        Load event data from a file containing JSON.
        """
        with path.open() as fileHandle:
            eventJSON = objectFromJSONBytesIO(fileHandle)

            self._log.info("Creating event: {event}", event=event)
            self.createEvent(event)

            # Load incidents
            for incidentJSON in eventJSON:
                try:
                    eventID = incidentJSON.get(IncidentJSONKey.event.value)
                    if eventID is None:
                        incidentJSON[IncidentJSONKey.event.value] = event.id
                    else:
                        if eventID != event.id:
                            raise ValueError(
                                f"Event ID {eventID} != {event.id}"
                            )

                    incident = modelObjectFromJSONObject(
                        incidentJSON, Incident
                    )
                except ValueError as e:
                    if trialRun:
                        number = incidentJSON.get(IncidentJSONKey.number.value)
                        self._log.critical(
                            "Unable to load incident #{number}: {error}",
                            number=number, error=e,
                        )
                    else:
                        raise

                for incidentType in incident.incidentTypes:
                    self.createIncidentType(incidentType, hidden=True)

                self._log.info(
                    "Creating incident in {event}: {incident}",
                    event=event, incident=incident
                )
                if not trialRun:
                    self.importIncident(incident)


    ###
    # Events
    ###


    async def events(self) -> Iterable[Event]:
        """
        See :meth:`IMSDataStore.events`.
        """
        return (
            Event(id=row["name"]) for row in self._executeAndIterate(
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
        self._execute(
            (
                (self._query_createEvent, dict(eventID=event.id)),
            ),
            "Unable to create event {eventID}"
        )

        self._log.info(
            "Created event: {event}", storeWriteClass=Event, event=event,
        )

    _query_createEvent = _query(
        """
        insert into EVENT (NAME) values (:eventID);
        """
    )


    def _eventAccess(self, event: Event, mode: str) -> Iterable[str]:
        return (
            row["EXPRESSION"] for row in self._executeAndIterate(
                self._query_eventAccess,
                dict(eventID=event.id, mode=mode),
                "Unable to look up {mode} access for event {eventID}",
            )
        )

    _query_eventAccess = _query(
        """
        select EXPRESSION from EVENT_ACCESS
        where EVENT = ({query_eventID}) and MODE = :mode
        """
    )


    def _setEventAccess(
        self, event: Event, mode: str, expressions: Iterable[str]
    ) -> None:
        expressions = tuple(expressions)
        try:
            with self._db as db:
                cursor: Cursor = db.cursor()
                try:
                    cursor.execute(
                        self._query_clearEventAccessForMode,
                        dict(eventID=event.id, mode=mode),
                    )
                    for expression in expressions:
                        cursor.execute(
                            self._query_clearEventAccessForExpression,
                            dict(eventID=event.id, expression=expression),
                        )
                        cursor.execute(
                            self._query_addEventAccess, dict(
                                eventID=event.id,
                                expression=expression,
                                mode=mode,
                            )
                        )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self._log.critical(
                "Unable to set {mode} access for {event}: {error}",
                event=event, mode=mode, expressions=expressions, error=e,
            )
            raise StorageError(e)

        self._log.info(
            "Set {mode} access for {event}: {expressions}",
            storeWriteClass=Event,
            event=event, mode=mode, expressions=expressions,
        )

    _query_clearEventAccessForMode = _query(
        """
        delete from EVENT_ACCESS
        where EVENT = ({query_eventID}) and MODE = :mode
        """
    )

    _query_clearEventAccessForExpression = _query(
        """
        delete from EVENT_ACCESS
        where EVENT = ({query_eventID}) and EXPRESSION = :expression
        """
    )

    _query_addEventAccess = _query(
        """
        insert into EVENT_ACCESS (EVENT, EXPRESSION, MODE)
        values (({query_eventID}), :expression, :mode)
        """
    )


    async def readers(self, event: Event) -> Iterable[str]:
        """
        See :meth:`IMSDataStore.readers`.
        """
        assert type(event) is Event

        return self._eventAccess(event, "read")


    async def setReaders(self, event: Event, readers: Iterable[str]) -> None:
        """
        See :meth:`IMSDataStore.setReaders`.
        """
        return self._setEventAccess(event, "read", readers)


    async def writers(self, event: Event) -> Iterable[str]:
        """
        See :meth:`IMSDataStore.writers`.
        """
        assert type(event) is Event

        return self._eventAccess(event, "write")


    async def setWriters(self, event: Event, writers: Iterable[str]) -> None:
        """
        See :meth:`IMSDataStore.setWriters`.
        """
        return self._setEventAccess(event, "write", writers)


    ###
    # Incident Types
    ###


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

        self._log.info(
            "Created incident type: {incidentType} (hidden={hidden})",
            # storeWriteClass=IncidentType,
            incidentType=incidentType, hidden=hidden,
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
        incidentTypes = tuple(incidentTypes)
        self._execute(
            (
                (
                    self._query_hideShowIncidentType,
                    dict(incidentType=incidentType, hidden=hidden),
                )
                for incidentType in incidentTypes
            ),
            f"Unable to set hidden to {hidden} incident types "
            f"{{incidentTypes}}"
        )

        self._log.info(
            "Set hidden to {hidden} for incident types: {incidentTypes}",
            # storeWriteClass=IncidentType,
            incidentTypes=incidentTypes, hidden=hidden,
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


    ###
    # Concentric Streets
    ###


    async def concentricStreets(self, event: Event) -> Mapping[str, str]:
        """
        See :meth:`IMSDataStore.concentricStreets`.
        """
        return MappingProxyType(dict(
            (row["ID"], row["NAME"]) for row in
            self._executeAndIterate(
                self._query_concentricStreets, dict(eventID=event.id),
                "Unable to look up concentric streets for event {eventID}"
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
        self._execute(
            ((
                self._query_createConcentricStreet,
                dict(eventID=event.id, streetID=id, streetName=name)
            ),),
            "Unable to create concentric street ({streetID}){streetName} "
            "for event {event}"
        )

        self._log.info(
            "Created concentric street in {event}: {streetName}",
            storeWriteClass=Event, event=event, concentricStreetName=name,
        )

    _query_createConcentricStreet = _query(
        """
        insert into CONCENTRIC_STREET (EVENT, ID, NAME)
        values (({query_eventID}), :streetID, :streetName)
        """
    )


    ##
    # Report Entries
    ##

    def detachedReportEntries(self) -> Iterable[ReportEntry]:
        """
        Look up all report entries that are not attached to either an incident
        or an incident report.
        There shouldn't be any of these; so if there are any, it's an
        indication of a bug.
        """
        try:
            with self._db as db:
                cursor: Cursor = db.cursor()
                try:
                    # FIXME: This should be an async generator
                    return tuple(
                        ReportEntry(
                            created=fromTimeStamp(row["CREATED"]),
                            author=row["AUTHOR"],
                            automatic=bool(row["GENERATED"]),
                            text=row["TEXT"],
                        )
                        for row in cast(Cursor, cursor.execute(
                            self._query_detachedReportEntries, {}
                        )) if row["TEXT"]
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self._log.critical(
                "Unable to look up detached report entries: {error}",
                error=e,
            )
            raise StorageError(e)

    _query_detachedReportEntries = _query(
        """
        select AUTHOR, TEXT, CREATED, GENERATED from REPORT_ENTRY
        where
            ID not in (select REPORT_ENTRY from INCIDENT__REPORT_ENTRY) and
            ID not in (select REPORT_ENTRY from INCIDENT_REPORT__REPORT_ENTRY)
        """
    )


    ###
    # Incidents
    ###


    def _fetchIncident(
        self, event: Event, incidentNumber: int, cursor: Cursor
    ) -> Incident:
        params: Parameters = dict(
            eventID=event.id, incidentNumber=incidentNumber
        )

        def notFound() -> None:
            raise NoSuchIncidentError(
                f"No incident #{incidentNumber} in event {event}"
            )

        try:
            cursor.execute(self._query_incident, params)
        except OverflowError:
            notFound()

        row = cursor.fetchone()
        if row is None:
            notFound()

        rangerHandles = tuple(
            row["RANGER_HANDLE"]
            for row in cast(Cursor, cursor.execute(
                self._query_incident_rangers, params
            ))
        )

        incidentTypes = tuple(
            row["NAME"]
            for row in cast(Cursor, cursor.execute(
                self._query_incident_types, params
            ))
        )

        reportEntries = tuple(
            ReportEntry(
                created=fromTimeStamp(row["CREATED"]),
                author=row["AUTHOR"],
                automatic=bool(row["GENERATED"]),
                text=row["TEXT"],
            )
            for row in cast(Cursor, cursor.execute(
                self._query_incident_reportEntries, params
            )) if row["TEXT"]
        )

        # FIXME: This is because schema thinks concentric is an int
        if row["LOCATION_CONCENTRIC"] is None:
            concentric = None
        else:
            concentric = str(row["LOCATION_CONCENTRIC"])

        return Incident(
            event=event,
            number=incidentNumber,
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
        for row in cast(Cursor, cursor.execute(
            self._query_incidentNumbers, dict(eventID=event.id)
        )):
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
                cursor: Cursor = db.cursor()
                try:
                    # FIXME: This should be an async generator
                    return tuple(
                        self._fetchIncident(event, number, cursor)
                        for number in
                        tuple(self._fetchIncidentNumbers(event, cursor))
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self._log.critical(
                "Unable to look up incidents in {event}: {error}",
                event=event, error=e,
            )
            raise StorageError(e)


    async def incidentWithNumber(self, event: Event, number: int) -> Incident:
        """
        See :meth:`IMSDataStore.incidentWithNumber`.
        """
        try:
            with self._db as db:
                cursor: Cursor = db.cursor()
                try:
                    return self._fetchIncident(event, number, cursor)
                finally:
                    cursor.close()
        except SQLiteError as e:
            self._log.critical(
                "Unable to look up incident #{number} in {event}: {error}",
                event=event, number=number, error=e,
            )
            raise StorageError(e)


    def _nextIncidentNumber(self, event: Event, cursor: Cursor) -> int:
        """
        Look up the next available incident number.
        """
        cursor.execute(self._query_maxIncidentNumber, dict(eventID=event.id))
        number = cursor.fetchone()["max(NUMBER)"]
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
        rangerHandles = tuple(rangerHandles)

        for rangerHandle in rangerHandles:
            cursor.execute(
                self._query_attachRangeHandleToIncident, dict(
                    eventID=event.id,
                    incidentNumber=incidentNumber,
                    rangerHandle=rangerHandle,
                )
            )

        self._log.info(
            "Attached Rangers {rangerHandles} to incident "
            "{event}#{incidentNumber}",
            storeWriteClass=Incident,
            event=event,
            incidentNumber=incidentNumber,
            rangerHandles=rangerHandles,
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
        incidentTypes = tuple(incidentTypes)

        for incidentType in incidentTypes:
            cursor.execute(
                self._query_attachIncidentTypeToIncident, dict(
                    eventID=event.id,
                    incidentNumber=incidentNumber,
                    incidentType=incidentType,
                )
            )

        self._log.info(
            "Attached incident types {incidentTypes} to incident "
            "{event}#{incidentNumber}",
            storeWriteClass=Incident,
            event=event,
            incidentNumber=incidentNumber,
            incidentTypes=incidentTypes,
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
        cursor.execute(
            self._query_addReportEntry, dict(
                created=asTimeStamp(reportEntry.created),
                generated=reportEntry.automatic,
                author=reportEntry.author,
                text=reportEntry.text,
            )
        )

        self._log.info(
            "Created report entry: {reportEntry}",
            storeWriteClass=ReportEntry, reportEntry=reportEntry,
        )

    _query_addReportEntry = _query(
        """
        insert into REPORT_ENTRY (AUTHOR, TEXT, CREATED, GENERATED)
        values (:author, :text, :created, :generated)
        """
    )


    def _createAndAttachReportEntriesToIncident(
        self, event: Event, incidentNumber: int,
        reportEntries: Iterable[ReportEntry], cursor: Cursor,
    ) -> None:
        reportEntries = tuple(reportEntries)

        for reportEntry in reportEntries:
            self._createReportEntry(reportEntry, cursor)

            # Join to incident
            cursor.execute(
                self._query_attachReportEntryToIncident, dict(
                    eventID=event.id,
                    incidentNumber=incidentNumber,
                    reportEntryID=cursor.lastrowid,
                )
            )

        self._log.info(
            "Attached report entries to incident {event}#{incidentNumber}: "
            "{reportEntries}",
            storeWriteClass=Incident,
            event=event,
            incidentNumber=incidentNumber,
            reportEntries=reportEntries,
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
            text=f"Changed {attribute} to: {value}",
            author=author, created=created, automatic=True,
        )


    def _initialReportEntries(
        self, incident: Union[Incident, IncidentReport], author: str
    ) -> Iterable[ReportEntry]:
        created = now()

        reportEntries = []

        def addEntry(attribute: str, value: Any) -> None:
            reportEntries.append(
                self._automaticReportEntry(
                    author, created, attribute, value
                )
            )

        if incident.summary:
            addEntry("summary", incident.summary)

        if isinstance(incident, Incident):
            if incident.priority != IncidentPriority.normal:
                addEntry("priority", incident.priority)

            if incident.state != IncidentState.new:
                addEntry("state", incident.state)

            location = incident.location
            if location.name:
                addEntry("location name", location.name)

            address = location.address
            if address is not None:
                if address.description:
                    addEntry("location description", address.description)

                if isinstance(address, RodGarettAddress):
                    if address.concentric is not None:
                        addEntry(
                            "location concentric street", address.concentric
                        )
                    if address.radialHour is not None:
                        addEntry("location radial hour", address.radialHour)
                    if address.radialMinute is not None:
                        addEntry(
                            "location radial minute", address.radialMinute
                        )

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
            assert not author
            assert incident.number > 0
        else:
            assert author
            assert incident.number == 0

            for reportEntry in incident.reportEntries:
                assert not reportEntry.automatic

            # Add initial report entries
            reportEntries = self._initialReportEntries(incident, author)
            incident = incident.replace(
                reportEntries=(reportEntries + incident.reportEntries)
            )

        # Get normalized-to-Rod-Garett address fields
        location = incident.location
        address = location.address

        assert address is not None

        locationDescription = address.description

        if isinstance(address, RodGarettAddress):
            locationConcentric   = address.concentric
            locationRadialHour   = address.radialHour
            locationRadialMinute = address.radialMinute
        else:
            locationConcentric   = None
            locationRadialHour   = None
            locationRadialMinute = None

        try:
            with self._db as db:
                cursor: Cursor = db.cursor()
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
                            locationDescription=locationDescription,
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
                    self._createAndAttachReportEntriesToIncident(
                        incident.event, incident.number,
                        incident.reportEntries, cursor,
                    )

                    return incident
                finally:
                    cursor.close()
        except SQLiteError as e:
            self._log.critical(
                "Unable to create incident {incident}: {error}",
                incident=incident, author=author, error=e,
            )
            raise StorageError(e)

        self._log.info(
            "Created incident {incident}",
            storeWriteClass=Incident, incident=incident,
        )


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
        See :meth:`IMSDataStore.importIncident`.
        """
        await self._createIncident(incident, None, True)


    def _setIncidentAttribute(
        self, query: str, event: Event, incidentNumber: int,
        attribute: str, value: ParameterValue, author: str,
    ) -> None:
        autoEntry = self._automaticReportEntry(
            author, now(), attribute, value
        )

        try:
            with self._db as db:
                cursor: Cursor = db.cursor()
                try:
                    cursor.execute(query, dict(
                        eventID=event.id,
                        incidentNumber=incidentNumber,
                        column=attribute,
                        value=value,
                    ))

                    # Add automatic report entry
                    self._createAndAttachReportEntriesToIncident(
                        event, incidentNumber, (autoEntry,), cursor,
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self._log.critical(
                "Author {author} unable to update incident #{incidentNumber} "
                "in event {event} ({attribute}={value}): {error}",
                query=query,
                event=event,
                incidentNumber=incidentNumber,
                attribute=attribute,
                value=value,
                author=author,
                error=e,
            )
            raise StorageError(e)

        self._log.info(
            "{author} updated incident {event}#{incidentNumber}: "
            "{attribute}={value}",
            storeWriteClass=Incident,
            query=query,
            event=event,
            incidentNumber=incidentNumber,
            attribute=attribute,
            value=value,
            author=author,
        )

    _template_setIncidentAttribute = _query(
        """
        update INCIDENT set {{column}} = :value
        where EVENT = ({query_eventID}) and NUMBER = :incidentNumber
        """
    )


    async def setIncident_priority(
        self, event: Event, incidentNumber: int, priority: IncidentPriority,
        author: str,
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_priority`.
        """
        self._setIncidentAttribute(
            self._query_setIncident_priority,
            event, incidentNumber, "priority", priorityAsID(priority), author,
        )

    _query_setIncident_priority = _template_setIncidentAttribute.format(
        column="PRIORITY"
    )


    async def setIncident_state(
        self, event: Event, incidentNumber: int, state: IncidentState,
        author: str,
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_state`.
        """
        self._setIncidentAttribute(
            self._query_setIncident_state,
            event, incidentNumber, "state", incidentStateAsID(state), author,
        )

    _query_setIncident_state = _template_setIncidentAttribute.format(
        column="STATE"
    )


    async def setIncident_summary(
        self, event: Event, incidentNumber: int, summary: str, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_summary`.
        """
        self._setIncidentAttribute(
            self._query_setIncident_summary,
            event, incidentNumber, "summary", summary, author,
        )

    _query_setIncident_summary = _template_setIncidentAttribute.format(
        column="SUMMARY"
    )


    async def setIncident_locationName(
        self, event: Event, incidentNumber: int, name: str, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_locationName`.
        """
        self._setIncidentAttribute(
            self._query_setIncident_locationName,
            event, incidentNumber, "location name", name, author,
        )

    _query_setIncident_locationName = _template_setIncidentAttribute.format(
        column="LOCATION_NAME"
    )


    async def setIncident_locationConcentricStreet(
        self, event: Event, incidentNumber: int, streetID: str, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_locationConcentricStreet`.
        """
        self._setIncidentAttribute(
            self._query_setIncident_locationConcentricStreet,
            event, incidentNumber, "location concentric street", streetID,
            author,
        )

    _query_setIncident_locationConcentricStreet = (
        _template_setIncidentAttribute.format(column="LOCATION_CONCENTRIC")
    )


    async def setIncident_locationRadialHour(
        self, event: Event, incidentNumber: int, hour: int, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_locationRadialHour`.
        """
        self._setIncidentAttribute(
            self._query_setIncident_locationRadialHour,
            event, incidentNumber, "location radial hour", hour, author,
        )

    _query_setIncident_locationRadialHour = (
        _template_setIncidentAttribute.format(column="LOCATION_RADIAL_HOUR")
    )


    async def setIncident_locationRadialMinute(
        self, event: Event, incidentNumber: int, minute: int, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_locationRadialMinute`.
        """
        self._setIncidentAttribute(
            self._query_setIncident_locationRadialMinute,
            event, incidentNumber, "location radial minute", minute, author,
        )

    _query_setIncident_locationRadialMinute = (
        _template_setIncidentAttribute.format(column="LOCATION_RADIAL_MINUTE")
    )


    async def setIncident_locationDescription(
        self, event: Event, incidentNumber: int, description: str, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_locationDescription`.
        """
        self._setIncidentAttribute(
            self._query_setIncident_locationRadialDescription,
            event, incidentNumber, "location description", description,
            author,
        )

    _query_setIncident_locationRadialDescription = (
        _template_setIncidentAttribute.format(
            column="LOCATION_DESCRIPTION"
        )
    )


    async def setIncident_rangers(
        self, event: Event, incidentNumber: int, rangerHandles: Iterable[str],
        author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_rangers`.
        """
        rangerHandles = frozenset(rangerHandles)

        autoEntry = self._automaticReportEntry(
            author, now(), "Rangers", ", ".join(rangerHandles)
        )

        try:
            with self._db as db:
                cursor: Cursor = db.cursor()
                try:
                    cursor.execute(
                        self._query_clearIncidentRangers,
                        dict(eventID=event.id, incidentNumber=incidentNumber)
                    )

                    self._attachRangeHandlesToIncident(
                        event, incidentNumber, rangerHandles, cursor
                    )

                    # Add automatic report entry
                    self._createAndAttachReportEntriesToIncident(
                        event, incidentNumber, (autoEntry,), cursor,
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self._log.critical(
                "Author {author} unable to attach Rangers {rangerHandles} to "
                "incident #{incidentNumber} in event {event}: {error}",
                author=author,
                rangerHandles=rangerHandles,
                incidentNumber=incidentNumber,
                event=event,
                error=e,
            )
            raise StorageError(e)

        self._log.info(
            "{author} set Rangers for incident {event}#{incidentNumber}: "
            "{rangerHandles}",
            storeWriteClass=Incident,
            author=author,
            event=event,
            incidentNumber=incidentNumber,
            rangerHandles=rangerHandles,
        )

    _query_clearIncidentRangers = _query(
        """
        delete from INCIDENT__RANGER
        where EVENT = ({query_eventID}) and INCIDENT_NUMBER = :incidentNumber
        """
    )


    async def setIncident_incidentTypes(
        self, event: Event, incidentNumber: int, incidentTypes: Iterable[str],
        author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncidentIncidentTypes`.
        """
        incidentTypes = frozenset(incidentTypes)

        autoEntry = self._automaticReportEntry(
            author, now(), "incident types", ", ".join(incidentTypes)
        )

        try:
            with self._db as db:
                cursor: Cursor = db.cursor()
                try:
                    cursor.execute(
                        self._query_clearIncidentIncidentTypes,
                        dict(eventID=event.id, incidentNumber=incidentNumber)
                    )

                    self._attachIncidentTypesToIncident(
                        event, incidentNumber, incidentTypes, cursor
                    )

                    # Add automatic report entry
                    self._createAndAttachReportEntriesToIncident(
                        event, incidentNumber, (autoEntry,), cursor,
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self._log.critical(
                "Author {author} unable to attach incident types "
                "{incidentTypes} to incident #{incidentNumber} in event "
                "{event}: {error}",
                author=author,
                incidentTypes=incidentTypes,
                incidentNumber=incidentNumber,
                event=event,
                error=e,
            )
            raise StorageError(e)

        self._log.info(
            "{author} set incident types for incident "
            "{event}#{incidentNumber}: {incidentTypes}",
            storeWriteClass=Incident,
            author=author,
            event=event,
            incidentNumber=incidentNumber,
            incidentTypes=incidentTypes,
        )

    _query_clearIncidentIncidentTypes = _query(
        """
        delete from INCIDENT__INCIDENT_TYPE
        where EVENT = ({query_eventID}) and INCIDENT_NUMBER = :incidentNumber
        """
    )


    async def addReportEntriesToIncident(
        self, event: Event, incidentNumber: int,
        reportEntries: Iterable[ReportEntry], author: str,
    ) -> None:
        """
        See :meth:`IMSDataStore.addReportEntriesToIncident`.
        """
        reportEntries = tuple(reportEntries)

        for reportEntry in reportEntries:
            if reportEntry.automatic:
                raise ValueError(
                    f"Automatic report entry {reportEntry} may not be created "
                    f"by user {author}"
                )

            if reportEntry.author != author:
                raise ValueError(
                    f"Report entry {reportEntry} has author != {author}"
                )

        try:
            with self._db as db:
                cursor: Cursor = db.cursor()
                try:
                    self._createAndAttachReportEntriesToIncident(
                        event, incidentNumber, reportEntries, cursor
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self._log.critical(
                "Author {author} unable to create report entries "
                "{reportEntries} to incident #{incidentNumber} in event "
                "{event}: {error}",
                author=author,
                reportEntries=reportEntries,
                incidentNumber=incidentNumber,
                event=event,
                error=e,
            )
            raise StorageError(e)


    ###
    # Incident Reports
    ###


    def _fetchIncidentReport(
        self, incidentReportNumber: int, cursor: Cursor
    ) -> IncidentReport:
        params: Parameters = dict(incidentReportNumber=incidentReportNumber)

        def notFound() -> None:
            raise NoSuchIncidentReportError(
                f"No incident report #{incidentReportNumber}"
            )

        try:
            cursor.execute(self._query_incidentReport, params)
        except OverflowError:
            notFound()

        row = cursor.fetchone()
        if row is None:
            notFound()


        reportEntries = tuple(
            ReportEntry(
                created=fromTimeStamp(row["CREATED"]),
                author=row["AUTHOR"],
                automatic=bool(row["GENERATED"]),
                text=row["TEXT"],
            )
            for row in cast(Cursor, cursor.execute(
                self._query_incidentReport_reportEntries, params
            ))
        )

        return IncidentReport(
            number=incidentReportNumber,
            created=fromTimeStamp(row["CREATED"]),
            summary=row["SUMMARY"],
            reportEntries=reportEntries,
        )

    _query_incidentReport = _query(
        """
        select CREATED, SUMMARY from INCIDENT_REPORT
        where NUMBER = :incidentReportNumber
        """
    )

    _query_incidentReport_reportEntries = _query(
        """
        select AUTHOR, TEXT, CREATED, GENERATED from REPORT_ENTRY
        where ID in (
            select REPORT_ENTRY from INCIDENT_REPORT__REPORT_ENTRY
            where INCIDENT_REPORT_NUMBER = :incidentReportNumber
        )
        """
    )


    def _fetchIncidentReportNumbers(self, cursor: Cursor) -> Iterable[int]:
        return (
            row["NUMBER"] for row in cast(Cursor, cursor.execute(
                self._query_incidentReportNumbers, {}
            ))
        )

    _query_incidentReportNumbers = _query(
        """
        select NUMBER from INCIDENT_REPORT
        """
    )


    async def incidentReports(self) -> Iterable[IncidentReport]:
        """
        See :meth:`IMSDataStore.incidentReports`.
        """
        try:
            with self._db as db:
                cursor: Cursor = db.cursor()
                try:
                    # FIXME: This should be an async generator
                    return tuple(
                        self._fetchIncidentReport(number, cursor)
                        for number
                        in tuple(self._fetchIncidentReportNumbers(cursor))
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self._log.critical(
                "Unable to look up incident reports: {error}", error=e,
            )
            raise StorageError(e)


    async def incidentReportWithNumber(self, number: int) -> IncidentReport:
        """
        See :meth:`IMSDataStore.incidentReportWithNumber`.
        """
        try:
            with self._db as db:
                cursor: Cursor = db.cursor()
                try:
                    return self._fetchIncidentReport(number, cursor)
                finally:
                    cursor.close()
        except SQLiteError as e:
            self._log.critical(
                "Unable to look up incident report #{number}: {error}",
                number=number, error=e,
            )
            raise StorageError(e)


    def _nextIncidentReportNumber(self, cursor: Cursor) -> int:
        """
        Look up the next available incident report number.
        """
        cursor.execute(self._query_maxIncidentReportNumber, {})
        number = cursor.fetchone()["max(NUMBER)"]
        if number is None:
            return 1
        else:
            return number + 1

    _query_maxIncidentReportNumber = _query(
        """
        select max(NUMBER) from INCIDENT_REPORT
        """
    )


    async def _createIncidentReport(
        self, incidentReport: IncidentReport, author: Optional[str],
        directImport: bool,
    ) -> IncidentReport:
        if directImport:
            assert author is None
            assert incidentReport.number > 0
        else:
            assert author
            assert incidentReport.number == 0

            for reportEntry in incidentReport.reportEntries:
                assert not reportEntry.automatic

            # Add initial report entries
            reportEntries = self._initialReportEntries(incidentReport, author)
            incidentReport = incidentReport.replace(
                reportEntries=(reportEntries + incidentReport.reportEntries)
            )

        try:
            with self._db as db:
                cursor: Cursor = db.cursor()
                try:
                    if not directImport:
                        # Assign the incident number a number
                        number = self._nextIncidentReportNumber(cursor)
                        incidentReport = incidentReport.replace(number=number)

                    # Write incident row
                    cursor.execute(
                        self._query_createIncidentReport, dict(
                            incidentReportNumber=incidentReport.number,
                            incidentReportCreated=asTimeStamp(
                                incidentReport.created
                            ),
                            incidentReportSummary=incidentReport.summary,
                        )
                    )

                    # Add report entries
                    self._createAndAttachReportEntriesToIncidentReport(
                        incidentReport.number, incidentReport.reportEntries,
                        cursor,
                    )

                    return incidentReport
                finally:
                    cursor.close()
        except SQLiteError as e:
            self._log.critical(
                "Unable to create incident report {incidentReport}: {error}",
                incidentReport=incidentReport, author=author, error=e,
            )
            raise StorageError(e)

        self._log.info(
            "Created incident report: {incidentReport}",
            storeWriteClass=IncidentReport, incidentReport=incidentReport,
        )

    _query_createIncidentReport = _query(
        """
        insert into INCIDENT_REPORT (NUMBER, CREATED, SUMMARY)
        values (
            :incidentReportNumber,
            :incidentReportCreated,
            :incidentReportSummary
        )
        """
    )


    def _createAndAttachReportEntriesToIncidentReport(
        self, incidentReportNumber: int, reportEntries: Iterable[ReportEntry],
        cursor: Cursor,
    ) -> None:
        for reportEntry in reportEntries:
            self._createReportEntry(reportEntry, cursor)

            # Join to incident
            cursor.execute(
                self._query_attachReportEntryToIncidentReport, dict(
                    incidentReportNumber=incidentReportNumber,
                    reportEntryID=cursor.lastrowid,
                )
            )

        self._log.info(
            "Attached report entries to incident report "
            "#{incidentReportNumber}: {reportEntry}",
            storeWriteClass=IncidentReport,
            incidentReportNumber=incidentReportNumber,
            reportEntries=reportEntries,
        )

    _query_attachReportEntryToIncidentReport = _query(
        """
        insert into INCIDENT_REPORT__REPORT_ENTRY (
            INCIDENT_REPORT_NUMBER, REPORT_ENTRY
        )
        values (:incidentReportNumber, :reportEntryID)
        """
    )


    async def createIncidentReport(
        self, incidentReport: IncidentReport, author: str
    ) -> IncidentReport:
        """
        See :meth:`IMSDataStore.createIncidentReport`.
        """
        return await self._createIncidentReport(incidentReport, author, False)


    def _setIncidentReportAttribute(
        self, query: str, incidentReportNumber: int,
        attribute: str, value: ParameterValue, author: str,
    ) -> None:
        autoEntry = self._automaticReportEntry(
            author, now(), attribute, value
        )

        try:
            with self._db as db:
                cursor: Cursor = db.cursor()
                try:
                    cursor.execute(query, dict(
                        incidentReportNumber=incidentReportNumber,
                        column=attribute,
                        value=value,
                    ))

                    # Add report entries
                    self._createAndAttachReportEntriesToIncidentReport(
                        incidentReportNumber, (autoEntry,), cursor,
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self._log.critical(
                "Author {author} unable to update incident report "
                "#{incidentReportNumber} ({attribute}={value}): {error}",
                query=query,
                incidentReportNumber=incidentReportNumber,
                attribute=attribute,
                value=value,
                author=author,
                error=e,
            )
            raise StorageError(e)

        self._log.info(
            "{author} updated incident report #{incidentReportNumber}: "
            "{attribute}={value}",
            storeWriteClass=IncidentReport,
            query=query,
            incidentReportNumber=incidentReportNumber,
            attribute=attribute,
            value=value,
            author=author,
        )

    _template_setIncidentReportAttribute = _query(
        """
        update INCIDENT_REPORT set {{column}} = :value
        where NUMBER = :incidentReportNumber
        """
    )


    async def setIncidentReport_summary(
        self, incidentReportNumber: int, summary: str, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncidentReport_summary`.
        """
        self._setIncidentReportAttribute(
            self._query_setIncidentReport_summary,
            incidentReportNumber, "summary", summary, author,
        )

    _query_setIncidentReport_summary = (
        _template_setIncidentReportAttribute.format(column="SUMMARY")
    )


    async def addReportEntriesToIncidentReport(
        self, incidentReportNumber: int, reportEntries: Iterable[ReportEntry],
        author: str,
    ) -> None:
        """
        See :meth:`IMSDataStore.addReportEntriesToIncidentReport`.
        """
        reportEntries = tuple(reportEntries)

        for reportEntry in reportEntries:
            if reportEntry.automatic:
                raise ValueError(
                    f"Automatic report entry {reportEntry} may not be created "
                    f"by user {author}"
                )

            if reportEntry.author != author:
                raise ValueError(
                    f"Report entry {reportEntry} has author != {author}"
                )

        try:
            with self._db as db:
                cursor: Cursor = db.cursor()
                try:
                    self._createAndAttachReportEntriesToIncidentReport(
                        incidentReportNumber, reportEntries, cursor
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self._log.critical(
                "Author {author} unable to create report entries "
                "{reportEntries} to incident report #{incidentReportNumber}: "
                "{error}",
                author=author,
                reportEntries=reportEntries,
                incidentReportNumber=incidentReportNumber,
                error=e,
            )
            raise StorageError(e)


    ###
    # Incident to Incident Report Relationships
    ###


    def _fetchDetachedIncidentReportNumbers(
        self, cursor: Cursor
    ) -> Iterable[int]:
        return (
            row["NUMBER"] for row in cast(Cursor, cursor.execute(
                self._query_detachedIncidentReportNumbers, {}
            ))
        )

    _query_detachedIncidentReportNumbers = _query(
        """
        select NUMBER from INCIDENT_REPORT
        where NUMBER not in (
            select INCIDENT_REPORT_NUMBER from INCIDENT__INCIDENT_REPORT
        )
        """
    )


    def _fetchAttachedIncidentReportNumbers(
        self, event: Event, incidentNumber: int, cursor: Cursor
    ) -> Iterable[int]:
        return (
            row["NUMBER"] for row in cast(Cursor, cursor.execute(
                self._query_attachedIncidentReportNumbers,
                dict(eventID=event.id, incidentNumber=incidentNumber)
            ))
        )

    _query_attachedIncidentReportNumbers = _query(
        """
        select NUMBER from INCIDENT_REPORT
        where NUMBER in (
            select INCIDENT_REPORT_NUMBER from INCIDENT__INCIDENT_REPORT
            where
                EVENT = ({query_eventID}) and
                INCIDENT_NUMBER = :incidentNumber
        )
        """
    )


    async def detachedIncidentReports(self) -> Iterable[IncidentReport]:
        """
        See :meth:`IMSDataStore.detachedIncidentReports`.
        """
        try:
            with self._db as db:
                cursor: Cursor = db.cursor()
                try:
                    # FIXME: This should be an async generator
                    return tuple(
                        self._fetchIncidentReport(number, cursor)
                        for number in tuple(
                            self._fetchDetachedIncidentReportNumbers(cursor)
                        )
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self._log.critical(
                "Unable to look up detached incident reports: {error}",
                error=e,
            )
            raise StorageError(e)


    async def incidentReportsAttachedToIncident(
        self, event: Event, incidentNumber: int
    ) -> Iterable[IncidentReport]:
        """
        See :meth:`IMSDataStore.attachedIncidentReports`.
        """
        try:
            with self._db as db:
                cursor: Cursor = db.cursor()
                try:
                    # FIXME: This should be an async generator
                    return tuple(
                        self._fetchIncidentReport(number, cursor)
                        for number in tuple(
                            self._fetchAttachedIncidentReportNumbers(
                                event, incidentNumber, cursor
                            )
                        )
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self._log.critical(
                "Unable to look up incident reports attached to incident "
                "#{incidentNumber} in event {event}: {error}",
                incidentNumber=incidentNumber,
                event=event,
                error=e,
            )
            raise StorageError(e)


    async def incidentsAttachedToIncidentReport(
        self, incidentReportNumber: int
    ) -> Iterable[Tuple[Event, int]]:
        """
        See :meth:`IMSDataStore.incidentsAttachedToIncidentReport`.
        """
        try:
            with self._db as db:
                cursor: Cursor = db.cursor()
                try:
                    # FIXME: This should be an async generator
                    return tuple(
                        (Event(row["EVENT"]), row["INCIDENT_NUMBER"])
                        for row in cast(Cursor, cursor.execute(
                            self._query_incidentsAttachedToIncidentReport,
                            dict(incidentReportNumber=incidentReportNumber)
                        ))
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self._log.critical(
                "Unable to look up incidents attached to incident report "
                "#{incidentReportNumber}: {error}",
                incidentReportNumber=incidentReportNumber,
                error=e,
            )
            raise StorageError(e)

    _query_incidentsAttachedToIncidentReport = _query(
        """
        select e.NAME as EVENT, iir.INCIDENT_NUMBER as INCIDENT_NUMBER
        from INCIDENT__INCIDENT_REPORT iir
        join EVENT e on e.ID = iir.EVENT
        where iir.INCIDENT_REPORT_NUMBER = :incidentReportNumber
        """
    )


    async def attachIncidentReportToIncident(
        self, incidentReportNumber: int, event: Event, incidentNumber: int
    ) -> None:
        """
        See :meth:`IMSDataStore.attachIncidentReportToIncident`.
        """
        try:
            with self._db as db:
                cursor: Cursor = db.cursor()
                try:
                    cursor.execute(
                        self._query_attachIncidentReportToIncident, dict(
                            eventID=event.id,
                            incidentNumber=incidentNumber,
                            incidentReportNumber=incidentReportNumber,
                        )
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self._log.critical(
                "Unable to attach incident report #{incidentReportNumber} to "
                "incident #{incidentNumber} in event {event}: {error}",
                incidentReportNumber=incidentReportNumber,
                incidentNumber=incidentNumber,
                event=event,
                error=e,
            )
            raise StorageError(e)

        self._log.info(
            "Attached incident report #{incidentReportNumber} to incident "
            "{event}#{incidentNumber}",
            storeWriteClass=Incident,
            incidentReportNumber=incidentReportNumber,
            event=event,
            incidentNumber=incidentNumber,
        )

    _query_attachIncidentReportToIncident = _query(
        """
        insert into INCIDENT__INCIDENT_REPORT (
            EVENT, INCIDENT_NUMBER, INCIDENT_REPORT_NUMBER
        )
        values (({query_eventID}), :incidentNumber, :incidentReportNumber)
        """
    )


    async def detachIncidentReportFromIncident(
        self, incidentReportNumber: int, event: Event, incidentNumber: int
    ) -> None:
        """
        See :meth:`IMSDataStore.detachIncidentReportFromIncident`.
        """
        try:
            with self._db as db:
                cursor: Cursor = db.cursor()
                try:
                    cursor.execute(
                        self._query_detachIncidentReportFromIncident, dict(
                            eventID=event.id,
                            incidentNumber=incidentNumber,
                            incidentReportNumber=incidentReportNumber,
                        )
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self._log.critical(
                "Unable to detach incident report #{incidentReportNumber} "
                "from incident #{incidentNumber} in event {event}: {error}",
                incidentReportNumber=incidentReportNumber,
                incidentNumber=incidentNumber,
                event=event,
                error=e,
            )
            raise StorageError(e)

        self._log.info(
            "Detached incident report #{incidentReportNumber} from incident "
            "{event}#{incidentNumber}",
            storeWriteClass=Incident,
            incidentReportNumber=incidentReportNumber,
            event=event,
            incidentNumber=incidentNumber,
        )

    _query_detachIncidentReportFromIncident = _query(
        """
        delete from INCIDENT__INCIDENT_REPORT
        where
            EVENT = ({query_eventID}) and
            INCIDENT_NUMBER = :incidentNumber and
            INCIDENT_REPORT_NUMBER = :incidentReportNumber
        """
    )



zeroTimeDelta = TimeDelta(0)


def now() -> DateTime:
    return DateTime.now(TimeZone.utc)


def asTimeStamp(dateTime: DateTime) -> float:
    assert dateTime.tzinfo is not None, repr(dateTime)
    timeStamp = dateTime.timestamp()
    if timeStamp < 0:
        raise StorageError(
            f"DateTime is before the UTC epoch: {dateTime}"
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
