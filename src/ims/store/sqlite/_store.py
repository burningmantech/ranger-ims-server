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
from typing import Any, Callable, Iterable, Optional, Tuple, Union
from typing.io import TextIO

from attr import Factory, attrib, attrs
from attr.validators import instance_of, optional

from twisted.logger import Logger

from ims.ext.json import objectFromJSONBytesIO
from ims.ext.sqlite import (
    Connection, Cursor, SQLiteError,
    createDB, explainQueryPlans, openDB, printSchema,
)
from ims.model import (
    Event, Incident, IncidentPriority, IncidentReport, IncidentState,
    ReportEntry, RodGarettAddress,
)
from ims.model.json import IncidentJSONKey, modelObjectFromJSONObject

from ._queries import queries
from .._db import DatabaseStore, ParameterValue, Parameters, Query, Rows
from .._exceptions import NoSuchIncidentReportError, StorageError


__all__ = ()


query_eventID = "select ID from EVENT where NAME = :eventID"



@attrs(frozen=True)
class DataStore(DatabaseStore):
    """
    Incident Management System SQLite data store.
    """

    _log = Logger()

    schemaVersion = 2
    schemaBasePath = Path(__file__).parent / "schema"
    sqlFileExtension = "sqlite"

    query = queries


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
        queries = (
            (getattr(cls.query, name).text, name)
            for name in sorted(vars(cls.query))
        )

        with createDB(None, cls.loadSchema()) as db:
            for line in explainQueryPlans(db, queries):
                print(line, file=out)
                print(file=out)


    @classmethod
    def _dbSchemaVersion(cls, db: Connection) -> int:
        try:
            for row in db.execute(cls.query.schemaVersion.text):
                return row["VERSION"]
            else:
                raise StorageError("Invalid schema: no version")

        except SQLiteError as e:
            if e.args[0] == "no such table: SCHEMA_INFO":
                return 0

            cls._log.critical(
                "Unable to {description}: {error}",
                description=cls.query.schemaVersion.description, error=e,
            )
            raise StorageError(e)


    @property
    def _db(self) -> Connection:
        if self._state.db is None:
            try:
                self._state.db = openDB(self.dbPath, schema="")

            except SQLiteError as e:
                self._log.critical(
                    "Unable to open SQLite database {dbPath}: {error}",
                    dbPath=self.dbPath, error=e,
                )
                raise StorageError(
                    f"Unable to open SQLite database {self.dbPath}: {e}"
                )

        return self._state.db


    async def disconnect(self) -> None:
        """
        See :meth:`DatabaseStore.disconnect`.
        """
        self._state.db = None


    async def runQuery(
        self, query: Query, parameters: Optional[Parameters] = None
    ) -> Rows:
        if parameters is None:
            parameters = {}

        try:
            return self._db.execute(query.text, parameters)

        except SQLiteError as e:
            self._log.critical(
                "Unable to {description}: {error}",
                description=query.description,
                query=query, **parameters, error=e,
            )
            raise StorageError(e)


    async def runOperation(
        self, query: Query, parameters: Optional[Parameters] = None
    ) -> None:
        await self.runQuery(query, parameters)


    async def runInteraction(self, interaction: Callable) -> Any:
        try:
            with self._db as db:
                return interaction(db.cursor())
        except SQLiteError as e:
            self._log.critical(
                "Interaction {interaction} failed: {error}",
                interaction=interaction, error=e,
            )
            raise StorageError(e)


    async def dbSchemaVersion(self) -> int:
        """
        See :meth:`DatabaseStore.dbSchemaVersion`.
        """
        return self._dbSchemaVersion(self._db)


    async def applySchema(self, sql: str) -> None:
        """
        See :meth:`IMSDataStore.applySchema`.
        """
        try:
            self._db.executescript(sql)
            self._db.validateConstraints()
            self._db.commit()
        except SQLiteError as e:
            raise StorageError(f"Unable to apply schema: {e}")


    def asIncidentStateValue(
        self, incidentState: IncidentState
    ) -> ParameterValue:
        return incidentStateAsID(incidentState)


    def fromIncidentStateValue(self, value: ParameterValue) -> IncidentState:
        return incidentStateFromID(value)


    def asIncidentPriorityValue(
        self, incidentPriority: IncidentPriority
    ) -> ParameterValue:
        return priorityAsID(incidentPriority)


    def fromIncidentPriorityValue(
        self, value: ParameterValue
    ) -> IncidentPriority:
        return priorityFromID(value)


    def asDateTimeValue(self, dateTime: DateTime) -> ParameterValue:
        return asTimeStamp(dateTime)


    def fromDateTimeValue(self, value: ParameterValue) -> DateTime:
        return fromTimeStamp(value)


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
        for reportEntry in await self.detachedReportEntries():
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
    # Incidents
    ###


    def _nextIncidentNumber(self, event: Event, cursor: Cursor) -> int:
        """
        Look up the next available incident number.
        """
        cursor.execute(
            self.query.maxIncidentNumber.text, dict(eventID=event.id)
        )
        number = cursor.fetchone()["max(NUMBER)"]
        if number is None:
            return 1
        else:
            return number + 1


    def _attachRangeHandlesToIncident(
        self, event: Event, incidentNumber: int, rangerHandles: Iterable[str],
        cursor: Cursor,
    ) -> None:
        rangerHandles = tuple(rangerHandles)

        for rangerHandle in rangerHandles:
            cursor.execute(
                self.query.attachRangeHandleToIncident.text, dict(
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


    def _attachIncidentTypesToIncident(
        self, event: Event, incidentNumber: int, incidentTypes: Iterable[str],
        cursor: Cursor,
    ) -> None:
        incidentTypes = tuple(incidentTypes)

        for incidentType in incidentTypes:
            cursor.execute(
                self.query.attachIncidentTypeToIncident.text, dict(
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


    def _createReportEntry(
        self, reportEntry: ReportEntry, cursor: Cursor
    ) -> None:
        cursor.execute(
            self.query.createReportEntry.text, dict(
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


    def _createAndAttachReportEntriesToIncident(
        self, event: Event, incidentNumber: int,
        reportEntries: Iterable[ReportEntry], cursor: Cursor,
    ) -> None:
        reportEntries = tuple(reportEntries)

        for reportEntry in reportEntries:
            self._createReportEntry(reportEntry, cursor)

            # Join to incident
            cursor.execute(
                self.query.attachReportEntryToIncident.text, dict(
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
                        self.query.createIncident.text, dict(
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


    async def setIncident_priority(
        self, event: Event, incidentNumber: int, priority: IncidentPriority,
        author: str,
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_priority`.
        """
        self._setIncidentAttribute(
            self.query.setIncident_priority.text,
            event, incidentNumber, "priority", priorityAsID(priority), author,
        )


    async def setIncident_state(
        self, event: Event, incidentNumber: int, state: IncidentState,
        author: str,
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_state`.
        """
        self._setIncidentAttribute(
            self.query.setIncident_state.text,
            event, incidentNumber, "state", incidentStateAsID(state), author,
        )


    async def setIncident_summary(
        self, event: Event, incidentNumber: int, summary: str, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_summary`.
        """
        self._setIncidentAttribute(
            self.query.setIncident_summary.text,
            event, incidentNumber, "summary", summary, author,
        )


    async def setIncident_locationName(
        self, event: Event, incidentNumber: int, name: str, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_locationName`.
        """
        self._setIncidentAttribute(
            self.query.setIncident_locationName.text,
            event, incidentNumber, "location name", name, author,
        )


    async def setIncident_locationConcentricStreet(
        self, event: Event, incidentNumber: int, streetID: str, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_locationConcentricStreet`.
        """
        self._setIncidentAttribute(
            self.query.setIncident_locationConcentricStreet.text,
            event, incidentNumber, "location concentric street", streetID,
            author,
        )


    async def setIncident_locationRadialHour(
        self, event: Event, incidentNumber: int, hour: int, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_locationRadialHour`.
        """
        self._setIncidentAttribute(
            self.query.setIncident_locationRadialHour.text,
            event, incidentNumber, "location radial hour", hour, author,
        )


    async def setIncident_locationRadialMinute(
        self, event: Event, incidentNumber: int, minute: int, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_locationRadialMinute`.
        """
        self._setIncidentAttribute(
            self.query.setIncident_locationRadialMinute.text,
            event, incidentNumber, "location radial minute", minute, author,
        )


    async def setIncident_locationDescription(
        self, event: Event, incidentNumber: int, description: str, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_locationDescription`.
        """
        self._setIncidentAttribute(
            self.query.setIncident_locationDescription.text,
            event, incidentNumber, "location description", description,
            author,
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
                        self.query.clearIncidentRangers.text,
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
                        self.query.clearIncidentIncidentTypes.text,
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
        parameters: Parameters = dict(
            incidentReportNumber=incidentReportNumber,
        )

        def notFound() -> None:
            raise NoSuchIncidentReportError(
                f"No incident report #{incidentReportNumber}"
            )

        try:
            cursor.execute(self.query.incidentReport.text, parameters)
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
            for row in cursor.execute(
                self.query.incidentReport_reportEntries.text, parameters
            )
        )

        return IncidentReport(
            number=incidentReportNumber,
            created=fromTimeStamp(row["CREATED"]),
            summary=row["SUMMARY"],
            reportEntries=reportEntries,
        )


    def _fetchIncidentReportNumbers(self, cursor: Cursor) -> Iterable[int]:
        return (
            row["NUMBER"] for row in cursor.execute(
                self.query.incidentReportNumbers.text, {}
            )
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
        cursor.execute(self.query.maxIncidentReportNumber.text, {})
        number = cursor.fetchone()["max(NUMBER)"]
        if number is None:
            return 1
        else:
            return number + 1


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
                        self.query.createIncidentReport.text, dict(
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


    def _createAndAttachReportEntriesToIncidentReport(
        self, incidentReportNumber: int, reportEntries: Iterable[ReportEntry],
        cursor: Cursor,
    ) -> None:
        for reportEntry in reportEntries:
            self._createReportEntry(reportEntry, cursor)

            # Join to incident
            cursor.execute(
                self.query.attachReportEntryToIncidentReport.text, dict(
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


    async def setIncidentReport_summary(
        self, incidentReportNumber: int, summary: str, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncidentReport_summary`.
        """
        self._setIncidentReportAttribute(
            self.query.setIncidentReport_summary.text,
            incidentReportNumber, "summary", summary, author,
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
            row["NUMBER"] for row in cursor.execute(
                self.query.detachedIncidentReportNumbers.text, {}
            )
        )


    def _fetchAttachedIncidentReportNumbers(
        self, event: Event, incidentNumber: int, cursor: Cursor
    ) -> Iterable[int]:
        return (
            row["NUMBER"] for row in cursor.execute(
                self.query.attachedIncidentReportNumbers.text,
                dict(eventID=event.id, incidentNumber=incidentNumber)
            )
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
                        for row in cursor.execute(
                            self.query.incidentsAttachedToIncidentReport.text,
                            dict(incidentReportNumber=incidentReportNumber)
                        )
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
                        self.query.attachIncidentReportToIncident.text, dict(
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
                        self.query.detachIncidentReportFromIncident.text,
                        dict(
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


def fromTimeStamp(timeStamp: ParameterValue) -> DateTime:
    if not isinstance(timeStamp, float):
        raise TypeError("Time stamp in SQLite store must be a float")

    return DateTime.fromtimestamp(timeStamp, tz=TimeZone.utc)


def incidentStateFromID(strValue: ParameterValue) -> IncidentState:
    if not isinstance(strValue, str):
        raise TypeError("Incident state in SQLite store must be a str")

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


def priorityFromID(intValue: ParameterValue) -> IncidentPriority:
    if not isinstance(intValue, int):
        raise TypeError("Incident priority in SQLite store must be an int")

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
