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
Incident Management System database tooling.
"""

from abc import abstractmethod
from datetime import datetime as DateTime
from datetime import timezone as TimeZone
from pathlib import Path
from textwrap import dedent
from types import MappingProxyType
from typing import (
    Any,
    Callable,
    ClassVar,
    Iterable,
    Iterator,
    Mapping,
    NoReturn,
    Optional,
    TypeVar,
    Union,
    cast,
)

from attr import attrib, attrs
from twisted.logger import Logger

from ims.model import (
    Event,
    Incident,
    IncidentPriority,
    IncidentReport,
    IncidentState,
    Location,
    ReportEntry,
    RodGarettAddress,
)

from ._abc import IMSDataStore
from ._exceptions import (
    NoSuchIncidentError,
    NoSuchIncidentReportError,
    StorageError,
)


__all__ = ()


ParameterValue = Optional[Union[bytes, str, int, float]]
Parameters = Mapping[str, ParameterValue]

Row = Parameters
Rows = Iterator[Row]

T = TypeVar("T")


def now() -> DateTime:
    return DateTime.now(TimeZone.utc)


@attrs(frozen=True, auto_attribs=True, kw_only=False)
class Query:
    description: str
    text: str = attrib(converter=dedent)


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class Queries:
    schemaVersion: Query
    events: Query
    createEvent: Query
    createEventOrIgnore: Query
    eventAccess: Query
    clearEventAccessForMode: Query
    clearEventAccessForExpression: Query
    addEventAccess: Query
    incidentTypes: Query
    incidentTypesNotHidden: Query
    createIncidentType: Query
    createIncidentTypeOrIgnore: Query
    hideShowIncidentType: Query
    concentricStreets: Query
    createConcentricStreet: Query
    createConcentricStreetOrIgnore: Query
    detachedReportEntries: Query
    incident: Query
    incident_rangers: Query
    incident_incidentTypes: Query
    incident_reportEntries: Query
    incidentNumbers: Query
    maxIncidentNumber: Query
    attachRangeHandleToIncident: Query
    attachIncidentTypeToIncident: Query
    createReportEntry: Query
    attachReportEntryToIncident: Query
    createIncident: Query
    setIncident_priority: Query
    setIncident_state: Query
    setIncident_summary: Query
    setIncident_locationName: Query
    setIncident_locationConcentricStreet: Query
    setIncident_locationRadialHour: Query
    setIncident_locationRadialMinute: Query
    setIncident_locationDescription: Query
    clearIncidentRangers: Query
    clearIncidentIncidentTypes: Query
    incidentReport: Query
    incidentReport_reportEntries: Query
    incidentReportNumbers: Query
    maxIncidentReportNumber: Query
    createIncidentReport: Query
    attachReportEntryToIncidentReport: Query
    setIncidentReport_summary: Query
    attachIncidentReportToIncident: Query
    detachedIncidentReportNumbers: Query
    attachedIncidentReportNumbers: Query


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class Transaction:
    lastrowid: int

    @abstractmethod
    def execute(
        self, sql: str, parameters: Optional[Parameters] = None
    ) -> None:
        """
        Executes an SQL statement.
        """

    @abstractmethod
    def executescript(self, sql_script: str) -> None:
        """
        Execute multiple SQL statements at once.
        """

    @abstractmethod
    def fetchone(self) -> Optional[Row]:
        """
        Fetch the next row.
        """

    @abstractmethod
    def fetchall(self) -> Rows:
        """
        Fetch all rows.
        """


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class DatabaseStore(IMSDataStore):
    """
    Incident Management System data store using a managed database.
    """

    _log: ClassVar[Logger] = Logger()

    schemaVersion: ClassVar[int]
    schemaBasePath: ClassVar[Path]
    sqlFileExtension: ClassVar[str]

    query: ClassVar[Queries]

    @staticmethod
    def asIncidentStateValue(incidentState: IncidentState) -> ParameterValue:
        return {
            IncidentState.new: "new",
            IncidentState.onHold: "on_hold",
            IncidentState.dispatched: "dispatched",
            IncidentState.onScene: "on_scene",
            IncidentState.closed: "closed",
        }[incidentState]

    @staticmethod
    def fromIncidentStateValue(value: ParameterValue) -> IncidentState:
        if not isinstance(value, str):
            raise TypeError("Incident state in SQLite store must be a str")

        return {
            "new": IncidentState.new,
            "on_hold": IncidentState.onHold,
            "dispatched": IncidentState.dispatched,
            "on_scene": IncidentState.onScene,
            "closed": IncidentState.closed,
        }[value]

    @staticmethod
    def asPriorityValue(priority: IncidentPriority) -> ParameterValue:
        return {
            IncidentPriority.high: 1,
            IncidentPriority.normal: 3,
            IncidentPriority.low: 4,
        }[priority]

    @staticmethod
    def fromPriorityValue(value: ParameterValue) -> IncidentPriority:
        if not isinstance(value, int):
            raise TypeError("Incident priority in SQLite store must be an int")

        return {
            1: IncidentPriority.high,
            2: IncidentPriority.high,
            3: IncidentPriority.normal,
            4: IncidentPriority.low,
            5: IncidentPriority.low,
        }[value]

    @staticmethod
    def asDateTimeValue(dateTime: DateTime) -> ParameterValue:
        """
        Convert a :class:`DateTime` to a date-time value for the database.
        This implementation returns a :class:`float`.
        """
        assert dateTime.tzinfo is not None, repr(dateTime)
        timeStamp = dateTime.timestamp()
        if timeStamp < 0:
            raise StorageError(f"DateTime is before the UTC epoch: {dateTime}")
        return timeStamp

    @staticmethod
    def fromDateTimeValue(value: ParameterValue) -> DateTime:
        """
        Convert a date-time value from the database to a :class:`DateTime`.
        This implementation requires :obj:`value` to be a :class:`float`.
        """
        if not isinstance(value, float):
            raise TypeError("Time stamp in SQLite store must be a float")

        return DateTime.fromtimestamp(value, tz=TimeZone.utc)

    @classmethod
    def loadSchema(cls, version: Optional[Union[int, str]] = None) -> str:
        """
        Read the schema file with the given version name.
        """
        if version is None:
            version = cls.schemaVersion

        name = f"{version}.{cls.sqlFileExtension}"
        path = cls.schemaBasePath / name
        return path.read_text()

    @property
    def dbManager(self) -> "DatabaseManager":
        return DatabaseManager(store=self)

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close any existing connections to the database.
        """

    @abstractmethod
    async def runQuery(
        self, query: Query, parameters: Optional[Parameters] = None
    ) -> Rows:
        """
        Execute the given query with the given parameters, returning the
        resulting rows.
        """

    @abstractmethod
    async def runOperation(
        self, query: Query, parameters: Optional[Parameters] = None
    ) -> None:
        """
        Execute the given query with the given parameters.
        """

    @abstractmethod
    async def runInteraction(
        self,
        interaction: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        Create a transaction and call the given interaction with the
        transaction as the sole argument.
        """

    @abstractmethod
    async def dbSchemaVersion(self) -> int:
        """
        The database's current schema version.
        """

    @abstractmethod
    async def applySchema(self, sql: str) -> None:
        """
        Apply the given schema to the database.
        """

    async def upgradeSchema(self, targetVersion: Optional[int] = None) -> None:
        """
        See :meth:`IMSDataStore.upgradeSchema`.
        """
        if await self.dbManager.upgradeSchema(targetVersion):
            await self.disconnect()

    async def validate(self) -> None:
        """
        See :meth:`IMSDataStore.validate`.
        """
        self._log.info("Validating data store...")

        valid = True

        # Check for detached report entries
        for reportEntry in await self.detachedReportEntries():
            self._log.error(
                "Found detached report entry: {reportEntry}",
                reportEntry=reportEntry,
            )
            valid = False

        if not valid:
            raise StorageError("Data store validation failed")

    ###
    # Events
    ###

    async def events(self) -> Iterable[Event]:
        """
        See :meth:`IMSDataStore.events`.
        """
        return (
            Event(id=cast(str, row["NAME"]))
            for row in await self.runQuery(self.query.events)
        )

    async def createEvent(self, event: Event) -> None:
        """
        See :meth:`IMSDataStore.createEvent`.
        """
        await self.runOperation(self.query.createEvent, dict(eventID=event.id))

        self._log.info(
            "Created event: {event}",
            storeWriteClass=Event,
            event=event,
        )

    async def _eventAccess(self, event: Event, mode: str) -> Iterable[str]:
        return (
            cast(str, row["EXPRESSION"])
            for row in await self.runQuery(
                self.query.eventAccess, dict(eventID=event.id, mode=mode)
            )
        )

    async def _setEventAccess(
        self, event: Event, mode: str, expressions: Iterable[str]
    ) -> None:
        expressions = tuple(expressions)

        def setEventAccess(txn: Transaction) -> None:
            txn.execute(
                self.query.clearEventAccessForMode.text,
                dict(eventID=event.id, mode=mode),
            )
            for expression in expressions:
                txn.execute(
                    self.query.clearEventAccessForExpression.text,
                    dict(eventID=event.id, expression=expression),
                )
                txn.execute(
                    self.query.addEventAccess.text,
                    dict(
                        eventID=event.id,
                        expression=expression,
                        mode=mode,
                    ),
                )

        try:
            await self.runInteraction(setEventAccess)
        except StorageError as e:
            self._log.critical(
                "Unable to set {mode} access for {event}: {error}",
                event=event,
                mode=mode,
                expressions=expressions,
                error=e,
            )
            raise

        self._log.info(
            "Set {mode} access for {event}: {expressions}",
            storeWriteClass=Event,
            event=event,
            mode=mode,
            expressions=expressions,
        )

    async def readers(self, event: Event) -> Iterable[str]:
        """
        See :meth:`IMSDataStore.readers`.
        """
        assert type(event) is Event

        return await self._eventAccess(event, "read")

    async def setReaders(self, event: Event, readers: Iterable[str]) -> None:
        """
        See :meth:`IMSDataStore.setReaders`.
        """
        await self._setEventAccess(event, "read", readers)

    async def writers(self, event: Event) -> Iterable[str]:
        """
        See :meth:`IMSDataStore.writers`.
        """
        assert type(event) is Event

        return await self._eventAccess(event, "write")

    async def setWriters(self, event: Event, writers: Iterable[str]) -> None:
        """
        See :meth:`IMSDataStore.setWriters`.
        """
        await self._setEventAccess(event, "write", writers)

    async def reporters(self, event: Event) -> Iterable[str]:
        """
        See :meth:`IMSDataStore.reporters`.
        """
        assert type(event) is Event

        return await self._eventAccess(event, "report")

    async def setReporters(self, event: Event, writers: Iterable[str]) -> None:
        """
        See :meth:`IMSDataStore.setReporters`.
        """
        await self._setEventAccess(event, "report", writers)

    ###
    # Incident Types
    ###

    async def incidentTypes(self, includeHidden: bool = False) -> Iterable[str]:
        """
        See :meth:`IMSDataStore.incidentTypes`.
        """
        if includeHidden:
            query = self.query.incidentTypes
        else:
            query = self.query.incidentTypesNotHidden

        return (cast(str, row["NAME"]) for row in await self.runQuery(query))

    async def createIncidentType(
        self, incidentType: str, hidden: bool = False
    ) -> None:
        """
        See :meth:`IMSDataStore.createIncidentType`.
        """
        await self.runOperation(
            self.query.createIncidentType,
            dict(incidentType=incidentType, hidden=hidden),
        )

        self._log.info(
            "Created incident type: {incidentType} (hidden={hidden})",
            incidentType=incidentType,
            hidden=hidden,
        )

    async def _hideShowIncidentTypes(
        self, incidentTypes: Iterable[str], hidden: bool
    ) -> None:
        incidentTypes = tuple(incidentTypes)

        def hideShowIncidentTypes(txn: Transaction) -> None:
            for incidentType in incidentTypes:
                txn.execute(
                    self.query.hideShowIncidentType.text,
                    dict(incidentType=incidentType, hidden=hidden),
                )

        try:
            await self.runInteraction(hideShowIncidentTypes)
        except StorageError as e:
            self._log.critical(
                "Unable to set hidden to {hidden} for incident types: "
                "{incidentTypes}",
                incidentTypes=incidentTypes,
                hidden=hidden,
            )
            raise StorageError(f"Unable to set hidden: {e}")

        self._log.info(
            "Set hidden to {hidden} for incident types: {incidentTypes}",
            incidentTypes=incidentTypes,
            hidden=hidden,
        )

    async def showIncidentTypes(self, incidentTypes: Iterable[str]) -> None:
        """
        See :meth:`IMSDataStore.showIncidentTypes`.
        """
        await self._hideShowIncidentTypes(incidentTypes, False)

    async def hideIncidentTypes(self, incidentTypes: Iterable[str]) -> None:
        """
        See :meth:`IMSDataStore.hideIncidentTypes`.
        """
        await self._hideShowIncidentTypes(incidentTypes, True)

    ###
    # Concentric Streets
    ###

    async def concentricStreets(self, event: Event) -> Mapping[str, str]:
        """
        See :meth:`IMSDataStore.concentricStreets`.
        """
        return MappingProxyType(
            {
                cast(str, row["ID"]): cast(str, row["NAME"])
                for row in await self.runQuery(
                    self.query.concentricStreets, dict(eventID=event.id)
                )
            }
        )

    async def createConcentricStreet(
        self, event: Event, id: str, name: str
    ) -> None:
        """
        See :meth:`IMSDataStore.createConcentricStreet`.
        """
        await self.runOperation(
            self.query.createConcentricStreet,
            dict(eventID=event.id, streetID=id, streetName=name),
        )

        self._log.info(
            "Created concentric street in {event}: {streetName}",
            storeWriteClass=Event,
            event=event,
            concentricStreetName=name,
        )

    ##
    # Report Entries
    ##

    async def detachedReportEntries(self) -> Iterable[ReportEntry]:
        """
        Look up all report entries that are not attached to either an incident
        or an incident report.
        There shouldn't be any of these; so if there are any, it's an
        indication of a bug.
        """

        def detachedReportEntries(txn: Transaction) -> Iterable[ReportEntry]:
            txn.execute(self.query.detachedReportEntries.text)
            return tuple(
                ReportEntry(
                    created=self.fromDateTimeValue(row["CREATED"]),
                    author=cast(str, row["AUTHOR"]),
                    automatic=bool(row["GENERATED"]),
                    text=cast(str, row["TEXT"]),
                )
                for row in txn.fetchall()
                if row["TEXT"]
            )

        try:
            return await self.runInteraction(detachedReportEntries)
        except StorageError as e:
            self._log.critical(
                "Unable to look up detached report entries: {error}",
                error=e,
            )
            raise

    ###
    # Incidents
    ###

    def _fetchIncident(
        self, event: Event, incidentNumber: int, txn: Transaction
    ) -> Incident:
        parameters: Parameters = dict(
            eventID=event.id, incidentNumber=incidentNumber
        )

        def notFound() -> NoReturn:
            raise NoSuchIncidentError(
                f"No incident #{incidentNumber} in event {event}"
            )

        try:
            txn.execute(self.query.incident.text, parameters)
        except OverflowError:
            notFound()

        row = txn.fetchone()
        if row is None:
            notFound()

        txn.execute(self.query.incident_rangers.text, parameters)
        rangerHandles = (
            cast(str, row["RANGER_HANDLE"]) for row in txn.fetchall()
        )

        txn.execute(self.query.incident_incidentTypes.text, parameters)
        incidentTypes = (cast(str, row["NAME"]) for row in txn.fetchall())

        txn.execute(self.query.incident_reportEntries.text, parameters)

        reportEntries = (
            ReportEntry(
                created=self.fromDateTimeValue(row["CREATED"]),
                author=cast(str, row["AUTHOR"]),
                automatic=bool(row["GENERATED"]),
                text=cast(str, row["TEXT"]),
            )
            for row in txn.fetchall()
            if row["TEXT"]
        )

        # FIXME: This is because schema thinks concentric is an int
        if row["LOCATION_CONCENTRIC"] is None:
            concentric = None
        else:
            concentric = str(row["LOCATION_CONCENTRIC"])

        incidentReportNumbers = self._fetchAttachedIncidentReportNumbers(
            event, incidentNumber, txn
        )

        return Incident(
            event=event,
            number=incidentNumber,
            created=self.fromDateTimeValue(row["CREATED"]),
            state=self.fromIncidentStateValue(row["STATE"]),
            priority=self.fromPriorityValue(row["PRIORITY"]),
            summary=cast(Optional[str], row["SUMMARY"]),
            location=Location(
                name=cast(str, row["LOCATION_NAME"]),
                address=RodGarettAddress(
                    concentric=concentric,
                    radialHour=cast(Optional[int], row["LOCATION_RADIAL_HOUR"]),
                    radialMinute=cast(
                        Optional[int], row["LOCATION_RADIAL_MINUTE"]
                    ),
                    description=cast(
                        Optional[str], row["LOCATION_DESCRIPTION"]
                    ),
                ),
            ),
            rangerHandles=cast(Iterable[str], rangerHandles),
            incidentTypes=cast(Iterable[str], incidentTypes),
            reportEntries=cast(Iterable[ReportEntry], reportEntries),
            incidentReportNumbers=incidentReportNumbers,
        )

    def _fetchIncidentNumbers(
        self, event: Event, txn: Transaction
    ) -> Iterable[int]:
        """
        Look up all incident numbers for the given event.
        """
        txn.execute(self.query.incidentNumbers.text, dict(eventID=event.id))
        return (cast(int, row["NUMBER"]) for row in txn.fetchall())

    async def incidents(self, event: Event) -> Iterable[Incident]:
        """
        See :meth:`IMSDataStore.incidents`.
        """

        def incidents(txn: Transaction) -> Iterable[Incident]:
            return tuple(
                self._fetchIncident(event, number, txn)
                for number in tuple(self._fetchIncidentNumbers(event, txn))
            )

        try:
            return await self.runInteraction(incidents)
        except NoSuchIncidentError:
            raise
        except StorageError as e:
            self._log.critical(
                "Unable to look up incidents in {event}: {error}",
                event=event,
                error=e,
            )
            raise

    async def incidentWithNumber(self, event: Event, number: int) -> Incident:
        """
        See :meth:`IMSDataStore.incidentWithNumber`.
        """

        def incidentWithNumber(txn: Transaction) -> Incident:
            return self._fetchIncident(event, number, txn)

        try:
            return await self.runInteraction(incidentWithNumber)
        except StorageError as e:
            self._log.critical(
                "Unable to look up incident #{number} in {event}: {error}",
                event=event,
                number=number,
                error=e,
            )
            raise

    def _nextIncidentNumber(self, event: Event, txn: Transaction) -> int:
        """
        Look up the next available incident number.
        """
        txn.execute(self.query.maxIncidentNumber.text, dict(eventID=event.id))
        row = txn.fetchone()
        assert row is not None
        number = cast(Optional[int], row["max(NUMBER)"])
        if number is None:
            return 1
        else:
            return number + 1

    def _attachRangeHandlesToIncident(
        self,
        event: Event,
        incidentNumber: int,
        rangerHandles: Iterable[str],
        txn: Transaction,
    ) -> None:
        rangerHandles = tuple(rangerHandles)

        for rangerHandle in rangerHandles:
            txn.execute(
                self.query.attachRangeHandleToIncident.text,
                dict(
                    eventID=event.id,
                    incidentNumber=incidentNumber,
                    rangerHandle=rangerHandle,
                ),
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
        self,
        event: Event,
        incidentNumber: int,
        incidentTypes: Iterable[str],
        txn: Transaction,
    ) -> None:
        incidentTypes = tuple(incidentTypes)

        for incidentType in incidentTypes:
            txn.execute(
                self.query.attachIncidentTypeToIncident.text,
                dict(
                    eventID=event.id,
                    incidentNumber=incidentNumber,
                    incidentType=incidentType,
                ),
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
        self, reportEntry: ReportEntry, txn: Transaction
    ) -> None:
        txn.execute(
            self.query.createReportEntry.text,
            dict(
                created=self.asDateTimeValue(reportEntry.created),
                generated=reportEntry.automatic,
                author=reportEntry.author,
                text=reportEntry.text,
            ),
        )

        self._log.info(
            "Created report entry: {reportEntry}",
            storeWriteClass=ReportEntry,
            reportEntry=reportEntry,
        )

    def _createAndAttachReportEntriesToIncident(
        self,
        event: Event,
        incidentNumber: int,
        reportEntries: Iterable[ReportEntry],
        txn: Transaction,
    ) -> None:
        reportEntries = tuple(reportEntries)

        for reportEntry in reportEntries:
            self._createReportEntry(reportEntry, txn)

            # Join to incident
            txn.execute(
                self.query.attachReportEntryToIncident.text,
                dict(
                    eventID=event.id,
                    incidentNumber=incidentNumber,
                    reportEntryID=txn.lastrowid,
                ),
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
            author=author,
            created=created,
            automatic=True,
        )

    def _initialReportEntries(
        self, incident: Union[Incident, IncidentReport], author: str
    ) -> Iterable[ReportEntry]:
        created = now()

        reportEntries = []

        def addEntry(attribute: str, value: Any) -> None:
            reportEntries.append(
                self._automaticReportEntry(author, created, attribute, value)
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
                        addEntry("location radial minute", address.radialMinute)

            if incident.rangerHandles:
                addEntry("Rangers", ", ".join(incident.rangerHandles))

            if incident.incidentTypes:
                addEntry("incident types", ", ".join(incident.incidentTypes))

        return tuple(reportEntries)

    async def _createIncident(
        self,
        incident: Incident,
        author: Optional[str],
        directImport: bool,
    ) -> Incident:
        if directImport:
            if author is not None:
                raise ValueError("Incident author may not be specified.")
            if incident.number <= 0:
                raise ValueError("Incident number must be greater than zero.")
        else:
            if not author:
                raise ValueError("Incident author is required.")
            if incident.number != 0:
                raise ValueError("Incident number must be zero.")

            for reportEntry in incident.reportEntries:
                assert not reportEntry.automatic

            # Add initial report entries
            reportEntries = tuple(self._initialReportEntries(incident, author))
            incident = incident.replace(
                reportEntries=(reportEntries + tuple(incident.reportEntries))
            )

        # Get normalized-to-Rod-Garett address fields
        location = incident.location
        address = location.address

        assert address is not None

        locationDescription = address.description

        if isinstance(address, RodGarettAddress):
            locationConcentric = address.concentric
            locationRadialHour = address.radialHour
            locationRadialMinute = address.radialMinute
        else:
            locationConcentric = None
            locationRadialHour = None
            locationRadialMinute = None

        def createIncident(
            txn: Transaction, incident: Incident = incident
        ) -> Incident:
            if not directImport:
                # Assign the incident number a number
                number = self._nextIncidentNumber(incident.event, txn)
                incident = incident.replace(number=number)

            # Write incident row
            txn.execute(
                self.query.createIncident.text,
                dict(
                    eventID=incident.event.id,
                    incidentNumber=incident.number,
                    incidentCreated=self.asDateTimeValue(incident.created),
                    incidentPriority=self.asPriorityValue(incident.priority),
                    incidentState=self.asIncidentStateValue(incident.state),
                    incidentSummary=incident.summary,
                    locationName=location.name,
                    locationConcentric=locationConcentric,
                    locationRadialHour=locationRadialHour,
                    locationRadialMinute=locationRadialMinute,
                    locationDescription=locationDescription,
                ),
            )

            # Join with Ranger handles
            self._attachRangeHandlesToIncident(
                incident.event,
                incident.number,
                incident.rangerHandles,
                txn,
            )

            # Attach incident types
            self._attachIncidentTypesToIncident(
                incident.event,
                incident.number,
                incident.incidentTypes,
                txn,
            )

            # Add report entries
            self._createAndAttachReportEntriesToIncident(
                incident.event,
                incident.number,
                incident.reportEntries,
                txn,
            )

            return incident

        try:
            incident = await self.runInteraction(createIncident)
        except StorageError as e:
            self._log.critical(
                "Unable to create incident {incident}: {error}",
                incident=incident,
                author=author,
                error=e,
            )
            raise

        self._log.info(
            "Created incident {incident}",
            storeWriteClass=Incident,
            incident=incident,
        )

        return incident

    async def createIncident(self, incident: Incident, author: str) -> Incident:
        """
        See :meth:`IMSDataStore.createIncident`.
        """
        return await self._createIncident(incident, author, False)

    async def importIncident(self, incident: Incident) -> None:
        """
        See :meth:`IMSDataStore.importIncident`.
        """
        await self._createIncident(incident, None, True)

    async def _setIncidentAttribute(
        self,
        query: str,
        event: Event,
        incidentNumber: int,
        attribute: str,
        value: ParameterValue,
        author: str,
    ) -> None:
        autoEntry = self._automaticReportEntry(author, now(), attribute, value)

        def setIncidentAttribute(txn: Transaction) -> None:
            txn.execute(
                query,
                dict(
                    eventID=event.id,
                    incidentNumber=incidentNumber,
                    value=value,
                ),
            )

            # Add automatic report entry
            self._createAndAttachReportEntriesToIncident(
                event,
                incidentNumber,
                (autoEntry,),
                txn,
            )

        try:
            await self.runInteraction(setIncidentAttribute)
        except StorageError as e:
            self._log.critical(
                "Author {author} unable to update incident "
                "{event}#{incidentNumber} ({attribute}={value}): {error}",
                query=query,
                event=event,
                incidentNumber=incidentNumber,
                attribute=attribute,
                value=value,
                author=author,
                error=e,
            )
            raise

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
        self,
        event: Event,
        incidentNumber: int,
        priority: IncidentPriority,
        author: str,
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_priority`.
        """
        await self._setIncidentAttribute(
            self.query.setIncident_priority.text,
            event,
            incidentNumber,
            "priority",
            self.asPriorityValue(priority),
            author,
        )

    async def setIncident_state(
        self,
        event: Event,
        incidentNumber: int,
        state: IncidentState,
        author: str,
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_state`.
        """
        await self._setIncidentAttribute(
            self.query.setIncident_state.text,
            event,
            incidentNumber,
            "state",
            self.asIncidentStateValue(state),
            author,
        )

    async def setIncident_summary(
        self, event: Event, incidentNumber: int, summary: str, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_summary`.
        """
        await self._setIncidentAttribute(
            self.query.setIncident_summary.text,
            event,
            incidentNumber,
            "summary",
            summary,
            author,
        )

    async def setIncident_locationName(
        self, event: Event, incidentNumber: int, name: str, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_locationName`.
        """
        await self._setIncidentAttribute(
            self.query.setIncident_locationName.text,
            event,
            incidentNumber,
            "location name",
            name,
            author,
        )

    async def setIncident_locationConcentricStreet(
        self, event: Event, incidentNumber: int, streetID: str, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_locationConcentricStreet`.
        """
        await self._setIncidentAttribute(
            self.query.setIncident_locationConcentricStreet.text,
            event,
            incidentNumber,
            "location concentric street",
            streetID,
            author,
        )

    async def setIncident_locationRadialHour(
        self, event: Event, incidentNumber: int, hour: int, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_locationRadialHour`.
        """
        await self._setIncidentAttribute(
            self.query.setIncident_locationRadialHour.text,
            event,
            incidentNumber,
            "location radial hour",
            hour,
            author,
        )

    async def setIncident_locationRadialMinute(
        self, event: Event, incidentNumber: int, minute: int, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_locationRadialMinute`.
        """
        await self._setIncidentAttribute(
            self.query.setIncident_locationRadialMinute.text,
            event,
            incidentNumber,
            "location radial minute",
            minute,
            author,
        )

    async def setIncident_locationDescription(
        self, event: Event, incidentNumber: int, description: str, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_locationDescription`.
        """
        await self._setIncidentAttribute(
            self.query.setIncident_locationDescription.text,
            event,
            incidentNumber,
            "location description",
            description,
            author,
        )

    async def setIncident_rangers(
        self,
        event: Event,
        incidentNumber: int,
        rangerHandles: Iterable[str],
        author: str,
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_rangers`.
        """
        rangerHandles = frozenset(rangerHandles)

        autoEntry = self._automaticReportEntry(
            author, now(), "Rangers", ", ".join(rangerHandles)
        )

        def setIncident_rangers(txn: Transaction) -> None:
            txn.execute(
                self.query.clearIncidentRangers.text,
                dict(eventID=event.id, incidentNumber=incidentNumber),
            )

            self._attachRangeHandlesToIncident(
                event, incidentNumber, rangerHandles, txn
            )

            # Add automatic report entry
            self._createAndAttachReportEntriesToIncident(
                event,
                incidentNumber,
                (autoEntry,),
                txn,
            )

        try:
            await self.runInteraction(setIncident_rangers)
        except StorageError as e:
            self._log.critical(
                "Author {author} unable to attach Rangers {rangerHandles} to "
                "incident #{incidentNumber} in event {event}: {error}",
                author=author,
                rangerHandles=rangerHandles,
                incidentNumber=incidentNumber,
                event=event,
                error=e,
            )
            raise

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
        self,
        event: Event,
        incidentNumber: int,
        incidentTypes: Iterable[str],
        author: str,
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncidentIncidentTypes`.
        """
        incidentTypes = frozenset(incidentTypes)

        autoEntry = self._automaticReportEntry(
            author, now(), "incident types", ", ".join(incidentTypes)
        )

        def setIncident_incidentTypes(txn: Transaction) -> None:
            txn.execute(
                self.query.clearIncidentIncidentTypes.text,
                dict(eventID=event.id, incidentNumber=incidentNumber),
            )

            self._attachIncidentTypesToIncident(
                event, incidentNumber, incidentTypes, txn
            )

            # Add automatic report entry
            self._createAndAttachReportEntriesToIncident(
                event,
                incidentNumber,
                (autoEntry,),
                txn,
            )

        try:
            await self.runInteraction(setIncident_incidentTypes)
        except StorageError as e:
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
            raise

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
        self,
        event: Event,
        incidentNumber: int,
        reportEntries: Iterable[ReportEntry],
        author: str,
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

        def addReportEntriesToIncident(txn: Transaction) -> None:
            self._createAndAttachReportEntriesToIncident(
                event, incidentNumber, reportEntries, txn
            )

        try:
            await self.runInteraction(addReportEntriesToIncident)
        except StorageError as e:
            self._log.critical(
                "Author {author} unable to create report entries "
                "{reportEntries} to incident "
                "{event}#{incidentNumber}: {error}",
                author=author,
                reportEntries=reportEntries,
                incidentNumber=incidentNumber,
                event=event,
                error=e,
            )
            raise

    ###
    # Incident Reports
    ###

    def _fetchIncidentReport(
        self, event: Event, incidentReportNumber: int, txn: Transaction
    ) -> IncidentReport:
        parameters: Parameters = dict(
            eventID=event.id,
            incidentReportNumber=incidentReportNumber,
        )

        def notFound() -> NoReturn:
            raise NoSuchIncidentReportError(
                f"No incident report #{incidentReportNumber}"
            )

        try:
            txn.execute(self.query.incidentReport.text, parameters)
        except OverflowError:
            notFound()

        row = txn.fetchone()
        if row is None:
            notFound()

        txn.execute(self.query.incidentReport_reportEntries.text, parameters)

        reportEntries = tuple(
            ReportEntry(
                created=self.fromDateTimeValue(row["CREATED"]),
                author=cast(str, row["AUTHOR"]),
                automatic=bool(row["GENERATED"]),
                text=cast(str, row["TEXT"]),
            )
            for row in txn.fetchall()
        )

        return IncidentReport(
            event=event,
            number=incidentReportNumber,
            created=self.fromDateTimeValue(row["CREATED"]),
            summary=cast(Optional[str], row["SUMMARY"]),
            incidentNumber=cast(Optional[int], row["INCIDENT_NUMBER"]),
            reportEntries=cast(Iterable[ReportEntry], reportEntries),
        )

    def _fetchIncidentReportNumbers(
        self, event: Event, txn: Transaction
    ) -> Iterable[int]:
        txn.execute(
            self.query.incidentReportNumbers.text, dict(eventID=event.id)
        )
        return (cast(int, row["NUMBER"]) for row in txn.fetchall())

    async def incidentReports(self, event: Event) -> Iterable[IncidentReport]:
        """
        See :meth:`IMSDataStore.incidentReports`.
        """

        def incidentReports(txn: Transaction) -> Iterable[IncidentReport]:
            return tuple(
                self._fetchIncidentReport(event, number, txn)
                for number in tuple(
                    self._fetchIncidentReportNumbers(event, txn)
                )
            )

        try:
            return await self.runInteraction(incidentReports)
        except NoSuchIncidentReportError:
            raise
        except StorageError as e:
            self._log.critical(
                "Unable to look up incident reports: {error}",
                error=e,
            )
            raise

    async def incidentReportWithNumber(
        self, event: Event, number: int
    ) -> IncidentReport:
        """
        See :meth:`IMSDataStore.incidentReportWithNumber`.
        """

        def incidentReportWithNumber(txn: Transaction) -> IncidentReport:
            return self._fetchIncidentReport(event, number, txn)

        try:
            return await self.runInteraction(incidentReportWithNumber)
        except StorageError as e:
            self._log.critical(
                "Unable to look up incident report #{number}: {error}",
                number=number,
                error=e,
            )
            raise

    def _nextIncidentReportNumber(self, txn: Transaction) -> int:
        """
        Look up the next available incident report number.
        """
        txn.execute(self.query.maxIncidentReportNumber.text)
        row = txn.fetchone()
        assert row is not None
        number = cast(Optional[int], row["max(NUMBER)"])
        if number is None:
            return 1
        else:
            return number + 1

    def _createAndAttachReportEntriesToIncidentReport(
        self,
        event: Event,
        incidentReportNumber: int,
        reportEntries: Iterable[ReportEntry],
        txn: Transaction,
    ) -> None:
        reportEntries = tuple(reportEntries)

        for reportEntry in reportEntries:
            self._createReportEntry(reportEntry, txn)

            # Join to incident
            txn.execute(
                self.query.attachReportEntryToIncidentReport.text,
                dict(
                    eventID=event.id,
                    incidentReportNumber=incidentReportNumber,
                    reportEntryID=txn.lastrowid,
                ),
            )

        self._log.info(
            "Attached report entries to incident report "
            "{event}#{incidentReportNumber}: {reportEntries}",
            storeWriteClass=IncidentReport,
            event=event,
            incidentReportNumber=incidentReportNumber,
            reportEntries=reportEntries,
        )

    async def _createIncidentReport(
        self,
        incidentReport: IncidentReport,
        author: Optional[str],
        directImport: bool,
    ) -> IncidentReport:
        if directImport:
            if author is not None:
                raise ValueError("Incident report author may not be specified.")
            if incidentReport.number <= 0:
                raise ValueError(
                    "Incident report number must be greater than zero."
                )
        else:
            if not author:
                raise ValueError("Incident report author is required.")
            if incidentReport.number != 0:
                raise ValueError("Incident report number must be zero.")

            for reportEntry in incidentReport.reportEntries:
                assert not reportEntry.automatic

            # Add initial report entries
            reportEntries = tuple(
                self._initialReportEntries(incidentReport, author)
            )
            incidentReport = incidentReport.replace(
                reportEntries=(
                    reportEntries + tuple(incidentReport.reportEntries)
                )
            )

        def createIncidentReport(
            txn: Transaction, incidentReport: IncidentReport = incidentReport
        ) -> IncidentReport:
            if not directImport:
                # Assign the incident number a number
                number = self._nextIncidentReportNumber(txn)
                incidentReport = incidentReport.replace(number=number)

            # Write incident row
            txn.execute(
                self.query.createIncidentReport.text,
                dict(
                    eventID=incidentReport.event.id,
                    incidentReportNumber=incidentReport.number,
                    incidentReportCreated=self.asDateTimeValue(
                        incidentReport.created
                    ),
                    incidentReportSummary=incidentReport.summary,
                    incidentNumber=incidentReport.incidentNumber,
                ),
            )

            # Add report entries
            self._createAndAttachReportEntriesToIncidentReport(
                incidentReport.event,
                incidentReport.number,
                incidentReport.reportEntries,
                txn,
            )

            return incidentReport

        try:
            incidentReport = await self.runInteraction(createIncidentReport)
        except StorageError as e:
            self._log.critical(
                "Unable to create incident report {incidentReport}: {error}",
                incidentReport=incidentReport,
                author=author,
                error=e,
            )
            raise

        self._log.info(
            "Created incident report: {incidentReport}",
            storeWriteClass=IncidentReport,
            incidentReport=incidentReport,
        )

        return incidentReport

    async def createIncidentReport(
        self, incidentReport: IncidentReport, author: str
    ) -> IncidentReport:
        """
        See :meth:`IMSDataStore.createIncidentReport`.
        """
        return await self._createIncidentReport(incidentReport, author, False)

    async def importIncidentReport(
        self, incidentReport: IncidentReport
    ) -> None:
        """
        See :meth:`IMSDataStore.importIncidentReport`.
        """
        await self._createIncidentReport(incidentReport, None, True)

    async def _setIncidentReportAttribute(
        self,
        query: str,
        event: Event,
        incidentReportNumber: int,
        attribute: str,
        value: ParameterValue,
        author: str,
    ) -> None:
        autoEntry = self._automaticReportEntry(author, now(), attribute, value)

        def setIncidentReportAttribute(txn: Transaction) -> None:
            txn.execute(
                query,
                dict(
                    eventID=event.id,
                    incidentReportNumber=incidentReportNumber,
                    value=value,
                ),
            )

            # Add report entries
            self._createAndAttachReportEntriesToIncidentReport(
                event,
                incidentReportNumber,
                (autoEntry,),
                txn,
            )

        try:
            await self.runInteraction(setIncidentReportAttribute)
        except StorageError as e:
            self._log.critical(
                "Author {author} unable to update incident report "
                "{event}#{incidentReportNumber} "
                "({attribute}={value}): {error}",
                query=query,
                event=event,
                incidentReportNumber=incidentReportNumber,
                attribute=attribute,
                value=value,
                author=author,
                error=e,
            )
            raise

        self._log.info(
            "{author} updated incident report #{incidentReportNumber}: "
            "{attribute}={value}",
            storeWriteClass=IncidentReport,
            query=query,
            event=event,
            incidentReportNumber=incidentReportNumber,
            attribute=attribute,
            value=value,
            author=author,
        )

    async def setIncidentReport_summary(
        self,
        event: Event,
        incidentReportNumber: int,
        summary: str,
        author: str,
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncidentReport_summary`.
        """
        await self._setIncidentReportAttribute(
            self.query.setIncidentReport_summary.text,
            event,
            incidentReportNumber,
            "summary",
            summary,
            author,
        )

    async def addReportEntriesToIncidentReport(
        self,
        event: Event,
        incidentReportNumber: int,
        reportEntries: Iterable[ReportEntry],
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

        def addReportEntriesToIncidentReport(txn: Transaction) -> None:
            self._createAndAttachReportEntriesToIncidentReport(
                event, incidentReportNumber, reportEntries, txn
            )

        try:
            await self.runInteraction(addReportEntriesToIncidentReport)
        except StorageError as e:
            self._log.critical(
                "Author {author} unable to create report entries "
                "{reportEntries} to incident report "
                "{event}#{incidentReportNumber}: {error}",
                author=author,
                reportEntries=reportEntries,
                incidentReportNumber=incidentReportNumber,
                event=event,
                error=e,
            )
            raise

    ###
    # Incident to Incident Report Relationships
    ###

    def _fetchDetachedIncidentReportNumbers(
        self, event: Event, txn: Transaction
    ) -> Iterable[int]:
        txn.execute(
            self.query.detachedIncidentReportNumbers.text,
            dict(eventID=event.id),
        )
        return (cast(int, row["NUMBER"]) for row in txn.fetchall())

    def _fetchAttachedIncidentReportNumbers(
        self, event: Event, incidentNumber: int, txn: Transaction
    ) -> Iterable[int]:
        txn.execute(
            self.query.attachedIncidentReportNumbers.text,
            dict(eventID=event.id, incidentNumber=incidentNumber),
        )
        return (cast(int, row["NUMBER"]) for row in txn.fetchall())

    async def incidentReportsAttachedToIncident(
        self, event: Event, incidentNumber: int
    ) -> Iterable[IncidentReport]:
        """
        See :meth:`IMSDataStore.attachedIncidentReports`.
        """

        def incidentReportsAttachedToIncident(
            txn: Transaction,
        ) -> Iterable[IncidentReport]:
            return tuple(
                self._fetchIncidentReport(event, number, txn)
                for number in tuple(
                    self._fetchAttachedIncidentReportNumbers(
                        event, incidentNumber, txn
                    )
                )
            )

        try:
            return await self.runInteraction(incidentReportsAttachedToIncident)
        except StorageError as e:
            self._log.critical(
                "Unable to look up incident reports attached to incident "
                "#{incidentNumber} in event {event}: {error}",
                incidentNumber=incidentNumber,
                event=event,
                error=e,
            )
            raise

    async def attachIncidentReportToIncident(
        self,
        incidentReportNumber: int,
        event: Event,
        incidentNumber: int,
        author: str,
    ) -> None:
        """
        See :meth:`IMSDataStore.attachIncidentReportToIncident`.
        """
        await self._setIncidentReportAttribute(
            self.query.attachIncidentReportToIncident.text,
            event,
            incidentReportNumber,
            "incident_number",
            incidentNumber,
            author,
        )

    async def detachIncidentReportFromIncident(
        self,
        incidentReportNumber: int,
        event: Event,
        incidentNumber: int,
        author: str,
    ) -> None:
        """
        See :meth:`IMSDataStore.detachIncidentReportFromIncident`.
        """
        await self._setIncidentReportAttribute(
            self.query.attachIncidentReportToIncident.text,
            event,
            incidentReportNumber,
            "incident_number",
            None,
            author,
        )


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class DatabaseManager:
    """
    Generic manager for databases.
    """

    _log: ClassVar[Logger] = Logger()

    store: DatabaseStore

    async def upgradeSchema(self, targetVersion: Optional[int] = None) -> bool:
        """
        Apply schema updates
        """
        if targetVersion is None:
            latestVersion = self.store.schemaVersion
        else:
            latestVersion = targetVersion

        currentVersion = await self.store.dbSchemaVersion()

        if currentVersion < 0:
            raise StorageError(
                f"No upgrade path from schema version {currentVersion}"
            )

        if currentVersion == latestVersion:
            # No upgrade needed
            self._log.debug(
                "No upgrade required for schema version {version}",
                version=currentVersion,
            )
            return False

        if currentVersion > latestVersion:
            raise StorageError(
                f"Schema version {currentVersion} is too new "
                f"(latest version is {latestVersion})"
            )

        async def sqlUpgrade(fromVersion: int, toVersion: int) -> None:
            self._log.info(
                "Upgrading database schema from version {fromVersion} to "
                "version {toVersion}",
                fromVersion=fromVersion,
                toVersion=toVersion,
            )

            if fromVersion == 0:
                fileID = f"{toVersion}"
            else:
                fileID = f"{toVersion}-from-{fromVersion}"

            try:
                try:
                    sql = self.store.loadSchema(version=fileID)
                except FileNotFoundError:
                    self._log.critical(
                        "Unable to upgrade schema in store {store.__class__} "
                        "from {fromVersion} to {toVersion} "
                        "due to missing schema upgrade file",
                        store=self.store,
                        fromVersion=fromVersion,
                        toVersion=toVersion,
                    )
                    raise StorageError("schema upgrade file not found")
                await self.store.applySchema(sql)
            except StorageError as e:
                raise StorageError(
                    f"Unable to upgrade schema from "
                    f"{fromVersion} to {toVersion}: {e}"
                )

        fromVersion = currentVersion

        while fromVersion < latestVersion:
            if fromVersion == 0:
                toVersion = latestVersion
            else:
                toVersion = fromVersion + 1

            await sqlUpgrade(fromVersion, toVersion)
            fromVersion = await self.store.dbSchemaVersion()

            # Make sure the schema version increased from last version
            if fromVersion <= currentVersion:
                raise StorageError(
                    f"Schema upgrade did not increase schema version "
                    f"({fromVersion} <= {currentVersion})"
                )
            currentVersion = fromVersion

        return True
