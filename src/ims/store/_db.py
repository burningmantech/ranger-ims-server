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
from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator, Mapping
from datetime import datetime as DateTime
from datetime import timezone as TimeZone
from json import loads
from pathlib import Path
from textwrap import dedent
from types import MappingProxyType
from typing import Any, ClassVar, NoReturn, Optional, TypeVar, Union, cast

from attrs import field, frozen
from twisted.logger import Logger

from ims.model import (
    Event,
    FieldReport,
    Incident,
    IncidentPriority,
    IncidentState,
    Location,
    ReportEntry,
    RodGarettAddress,
)

from ._abc import IMSDataStore
from ._exceptions import (
    NoSuchFieldReportError,
    NoSuchIncidentError,
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


@frozen
class Query:
    description: str
    text: str = field(converter=dedent)


@frozen(kw_only=True)
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
    incidents: Query
    incidents_reportEntries: Query
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
    fieldReport: Query
    fieldReport_reportEntries: Query
    fieldReportNumbers: Query
    maxFieldReportNumber: Query
    fieldReports: Query
    fieldReports_reportEntries: Query
    createFieldReport: Query
    attachReportEntryToFieldReport: Query
    setFieldReport_summary: Query
    attachFieldReportToIncident: Query
    detachedFieldReportNumbers: Query
    attachedFieldReportNumbers: Query


@frozen(kw_only=True)
class Transaction:
    lastrowid: int

    @abstractmethod
    def execute(self, sql: str, parameters: Parameters | None = None) -> None:
        """
        Executes an SQL statement.
        """

    @abstractmethod
    def executescript(self, sql_script: str) -> None:
        """
        Execute multiple SQL statements at once.
        """

    @abstractmethod
    def fetchone(self) -> Row | None:
        """
        Fetch the next row.
        """

    @abstractmethod
    def fetchall(self) -> Rows:
        """
        Fetch all rows.
        """


@frozen(kw_only=True)
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
    def loadSchema(cls, version: int | str | None = None) -> str:
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
        self, query: Query, parameters: Parameters | None = None
    ) -> Rows:
        """
        Execute the given query with the given parameters, returning the
        resulting rows.
        """

    @abstractmethod
    async def runOperation(
        self, query: Query, parameters: Parameters | None = None
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

    async def upgradeSchema(self, targetVersion: int | None = None) -> None:
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
        await self.runOperation(self.query.createEvent, {"eventID": event.id})

        self._log.info(
            "Created event: {event}",
            storeWriteClass=Event,
            event=event,
        )

    async def _eventAccess(self, eventID: str, mode: str) -> Iterable[str]:
        return (
            cast(str, row["EXPRESSION"])
            for row in await self.runQuery(
                self.query.eventAccess, {"eventID": eventID, "mode": mode}
            )
        )

    async def _setEventAccess(
        self, eventID: str, mode: str, expressions: Iterable[str]
    ) -> None:
        expressions = tuple(expressions)

        def setEventAccess(txn: Transaction) -> None:
            txn.execute(
                self.query.clearEventAccessForMode.text,
                {"eventID": eventID, "mode": mode},
            )
            for expression in expressions:
                txn.execute(
                    self.query.clearEventAccessForExpression.text,
                    {"eventID": eventID, "expression": expression},
                )
                txn.execute(
                    self.query.addEventAccess.text,
                    {
                        "eventID": eventID,
                        "expression": expression,
                        "mode": mode,
                    },
                )

        try:
            await self.runInteraction(setEventAccess)
        except StorageError as e:
            self._log.critical(
                "Unable to set {mode} access for {eventID}: {error}",
                eventID=eventID,
                mode=mode,
                expressions=expressions,
                error=e,
            )
            raise

        self._log.info(
            "Set {mode} access for {eventID}: {expressions}",
            storeWriteClass=Event,
            eventID=eventID,
            mode=mode,
            expressions=expressions,
        )

    async def readers(self, eventID: str) -> Iterable[str]:
        """
        See :meth:`IMSDataStore.readers`.
        """
        return await self._eventAccess(eventID, "read")

    async def setReaders(self, eventID: str, readers: Iterable[str]) -> None:
        """
        See :meth:`IMSDataStore.setReaders`.
        """
        await self._setEventAccess(eventID, "read", readers)

    async def writers(self, eventID: str) -> Iterable[str]:
        """
        See :meth:`IMSDataStore.writers`.
        """
        return await self._eventAccess(eventID, "write")

    async def setWriters(self, eventID: str, writers: Iterable[str]) -> None:
        """
        See :meth:`IMSDataStore.setWriters`.
        """
        await self._setEventAccess(eventID, "write", writers)

    async def reporters(self, eventID: str) -> Iterable[str]:
        """
        See :meth:`IMSDataStore.reporters`.
        """
        return await self._eventAccess(eventID, "report")

    async def setReporters(self, eventID: str, writers: Iterable[str]) -> None:
        """
        See :meth:`IMSDataStore.setReporters`.
        """
        await self._setEventAccess(eventID, "report", writers)

    ###
    # Incident Types
    ###

    async def incidentTypes(self, *, includeHidden: bool = False) -> Iterable[str]:
        """
        See :meth:`IMSDataStore.incidentTypes`.
        """
        if includeHidden:
            query = self.query.incidentTypes
        else:
            query = self.query.incidentTypesNotHidden

        return (cast(str, row["NAME"]) for row in await self.runQuery(query))

    async def createIncidentType(
        self, incidentType: str, *, hidden: bool = False
    ) -> None:
        """
        See :meth:`IMSDataStore.createIncidentType`.
        """
        await self.runOperation(
            self.query.createIncidentType,
            {"incidentType": incidentType, "hidden": hidden},
        )

        self._log.info(
            "Created incident type: {incidentType} (hidden={hidden})",
            incidentType=incidentType,
            hidden=hidden,
        )

    async def _hideShowIncidentTypes(
        self, incidentTypes: Iterable[str], *, hidden: bool
    ) -> None:
        incidentTypes = tuple(incidentTypes)

        def hideShowIncidentTypes(txn: Transaction) -> None:
            for incidentType in incidentTypes:
                txn.execute(
                    self.query.hideShowIncidentType.text,
                    {"incidentType": incidentType, "hidden": hidden},
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
            raise StorageError(f"Unable to set hidden: {e}") from e

        self._log.info(
            "Set hidden to {hidden} for incident types: {incidentTypes}",
            incidentTypes=incidentTypes,
            hidden=hidden,
        )

    async def showIncidentTypes(self, incidentTypes: Iterable[str]) -> None:
        """
        See :meth:`IMSDataStore.showIncidentTypes`.
        """
        await self._hideShowIncidentTypes(incidentTypes, hidden=False)

    async def hideIncidentTypes(self, incidentTypes: Iterable[str]) -> None:
        """
        See :meth:`IMSDataStore.hideIncidentTypes`.
        """
        await self._hideShowIncidentTypes(incidentTypes, hidden=True)

    ###
    # Concentric Streets
    ###

    async def concentricStreets(self, eventID: str) -> Mapping[str, str]:
        """
        See :meth:`IMSDataStore.concentricStreets`.
        """
        return MappingProxyType(
            {
                cast(str, row["ID"]): cast(str, row["NAME"])
                for row in await self.runQuery(
                    self.query.concentricStreets, {"eventID": eventID}
                )
            }
        )

    async def createConcentricStreet(self, eventID: str, id: str, name: str) -> None:
        """
        See :meth:`IMSDataStore.createConcentricStreet`.
        """
        await self.runOperation(
            self.query.createConcentricStreet,
            {"eventID": eventID, "streetID": id, "streetName": name},
        )

        self._log.info(
            "Created concentric street in {eventID}: {streetName}",
            storeWriteClass=Event,
            eventID=eventID,
            concentricStreetName=name,
        )

    ##
    # Report Entries
    ##

    async def detachedReportEntries(self) -> Iterable[ReportEntry]:
        """
        Look up all report entries that are not attached to either an incident
        or a field report.
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

    def _fetchIncidents(
        self, txn: Transaction, eventID: str, *, excludeSystemEntries: bool = False
    ) -> Iterable[Incident]:
        parameters: Parameters = {
            "eventID": eventID,
            # generated value less than or equal to
            "generatedLTE": 0 if excludeSystemEntries else 1,
        }

        reportEntries = defaultdict[int, list[ReportEntry]](list)
        txn.execute(self.query.incidents_reportEntries.text, parameters)
        for row in txn.fetchall():
            if row["TEXT"]:
                incidentNumber = cast(int, row["INCIDENT_NUMBER"])
                reportEntries[incidentNumber].append(
                    ReportEntry(
                        created=self.fromDateTimeValue(row["CREATED"]),
                        author=cast(str, row["AUTHOR"]),
                        automatic=bool(row["GENERATED"]),
                        text=cast(str, row["TEXT"]),
                    )
                )

        txn.execute(self.query.incidents.text, parameters)
        results = []
        for row in txn.fetchall():
            # FIXME: This is because schema thinks concentric is an int
            if row["LOCATION_CONCENTRIC"] is None:
                concentric = None
            else:
                concentric = str(row["LOCATION_CONCENTRIC"])

            rangerHandles = (
                loads(str(row["RANGER_HANDLES"])) if row["RANGER_HANDLES"] else []
            )
            incidentTypes = (
                loads(str(row["INCIDENT_TYPES"])) if row["INCIDENT_TYPES"] else []
            )
            fieldReportNumbers = []
            if row["FIELD_REPORT_NUMBERS"]:
                fieldReportNumbers = [
                    int(val) for val in loads(str(row["FIELD_REPORT_NUMBERS"]))
                ]
            incidentNumber = cast(int, row["NUMBER"])
            results.append(
                Incident(
                    eventID=eventID,
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
                    reportEntries=cast(
                        Iterable[ReportEntry], reportEntries[incidentNumber]
                    ),
                    fieldReportNumbers=cast(Iterable[int], fieldReportNumbers),
                )
            )
        return results

    def _fetchIncident(
        self, txn: Transaction, eventID: str, incidentNumber: int
    ) -> Incident:
        parameters: Parameters = {"eventID": eventID, "incidentNumber": incidentNumber}

        def notFound() -> NoReturn:
            raise NoSuchIncidentError(
                f"No incident #{incidentNumber} in event {eventID}"
            )

        try:
            txn.execute(self.query.incident.text, parameters)
        except OverflowError:
            notFound()

        row = txn.fetchone()
        if row is None:
            notFound()

        txn.execute(self.query.incident_rangers.text, parameters)
        rangerHandles = (cast(str, row["RANGER_HANDLE"]) for row in txn.fetchall())

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

        fieldReportNumbers = self._fetchAttachedFieldReportNumbers(
            txn, eventID, incidentNumber
        )

        return Incident(
            eventID=eventID,
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
                    radialMinute=cast(Optional[int], row["LOCATION_RADIAL_MINUTE"]),
                    description=cast(Optional[str], row["LOCATION_DESCRIPTION"]),
                ),
            ),
            rangerHandles=cast(Iterable[str], rangerHandles),
            incidentTypes=cast(Iterable[str], incidentTypes),
            reportEntries=cast(Iterable[ReportEntry], reportEntries),
            fieldReportNumbers=fieldReportNumbers,
        )

    def _fetchIncidentNumbers(self, txn: Transaction, eventID: str) -> Iterable[int]:
        """
        Look up all incident numbers for the given event.
        """
        txn.execute(self.query.incidentNumbers.text, {"eventID": eventID})
        return (cast(int, row["NUMBER"]) for row in txn.fetchall())

    async def incidents(
        self, eventID: str, *, excludeSystemEntries: bool = False
    ) -> Iterable[Incident]:
        """
        See :meth:`IMSDataStore.incidents`.
        """

        def incidents(txn: Transaction) -> Iterable[Incident]:
            return self._fetchIncidents(
                txn, eventID, excludeSystemEntries=excludeSystemEntries
            )

        try:
            return await self.runInteraction(incidents)
        except NoSuchIncidentError:
            raise
        except StorageError as e:
            self._log.critical(
                "Unable to look up incidents in {eventID}: {error}",
                eventID=eventID,
                error=e,
            )
            raise

    async def incidentWithNumber(self, eventID: str, number: int) -> Incident:
        """
        See :meth:`IMSDataStore.incidentWithNumber`.
        """

        def incidentWithNumber(txn: Transaction) -> Incident:
            return self._fetchIncident(txn, eventID, number)

        try:
            return await self.runInteraction(incidentWithNumber)
        except StorageError as e:
            self._log.critical(
                "Unable to look up incident #{number} in {eventID}: {error}",
                eventID=eventID,
                number=number,
                error=e,
            )
            raise

    def _nextIncidentNumber(self, eventID: str, txn: Transaction) -> int:
        """
        Look up the next available incident number.
        """
        txn.execute(self.query.maxIncidentNumber.text, {"eventID": eventID})
        row = txn.fetchone()
        assert row is not None
        number = cast(Optional[int], row["max(NUMBER)"])
        if number is None:
            return 1
        return number + 1

    def _attachRangeHandlesToIncident(
        self,
        eventID: str,
        incidentNumber: int,
        rangerHandles: Iterable[str],
        txn: Transaction,
    ) -> None:
        rangerHandles = tuple(rangerHandles)

        for rangerHandle in rangerHandles:
            txn.execute(
                self.query.attachRangeHandleToIncident.text,
                {
                    "eventID": eventID,
                    "incidentNumber": incidentNumber,
                    "rangerHandle": rangerHandle,
                },
            )

        self._log.info(
            "Attached Rangers {rangerHandles} to incident "
            "{eventID}#{incidentNumber}",
            eventID=eventID,
            incidentNumber=incidentNumber,
            rangerHandles=rangerHandles,
        )

    def _attachIncidentTypesToIncident(
        self,
        eventID: str,
        incidentNumber: int,
        incidentTypes: Iterable[str],
        txn: Transaction,
    ) -> None:
        incidentTypes = tuple(incidentTypes)

        for incidentType in incidentTypes:
            txn.execute(
                self.query.attachIncidentTypeToIncident.text,
                {
                    "eventID": eventID,
                    "incidentNumber": incidentNumber,
                    "incidentType": incidentType,
                },
            )

        self._log.info(
            "Attached incident types {incidentTypes} to incident "
            "{eventID}#{incidentNumber}",
            eventID=eventID,
            incidentNumber=incidentNumber,
            incidentTypes=incidentTypes,
        )

    def _createReportEntry(self, reportEntry: ReportEntry, txn: Transaction) -> None:
        txn.execute(
            self.query.createReportEntry.text,
            {
                "created": self.asDateTimeValue(reportEntry.created),
                "generated": reportEntry.automatic,
                "author": reportEntry.author,
                "text": reportEntry.text,
            },
        )

        self._log.info(
            "Created report entry: {reportEntry}",
            storeWriteClass=ReportEntry,
            reportEntry=reportEntry,
        )

    def _notifyIncidentUpdate(
        self,
        eventID: str,
        incidentNumber: int,
    ) -> None:
        # This will trigger the DataStoreEventSourceLogObserver
        self._log.info(
            "Firing incident update event for {eventID}#{incidentNumber}",
            storeWriteClass=Incident,
            eventID=eventID,
            incidentNumber=incidentNumber,
        )

    def _createAndAttachReportEntriesToIncident(
        self,
        eventID: str,
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
                {
                    "eventID": eventID,
                    "incidentNumber": incidentNumber,
                    "reportEntryID": txn.lastrowid,
                },
            )

        self._log.info(
            "Attached report entries to incident {eventID}#{incidentNumber}: "
            "{reportEntries}",
            eventID=eventID,
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
        self, incident: Incident | FieldReport, author: str
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
        self,
        incident: Incident,
        *,
        author: str | None,
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

        def createIncident(txn: Transaction, incident: Incident = incident) -> Incident:
            if not directImport:
                # Assign the incident number a number
                number = self._nextIncidentNumber(incident.eventID, txn)
                incident = incident.replace(number=number)

            # Write incident row
            txn.execute(
                self.query.createIncident.text,
                {
                    "eventID": incident.eventID,
                    "incidentNumber": incident.number,
                    "incidentCreated": self.asDateTimeValue(incident.created),
                    "incidentPriority": self.asPriorityValue(incident.priority),
                    "incidentState": self.asIncidentStateValue(incident.state),
                    "incidentSummary": incident.summary,
                    "locationName": location.name,
                    "locationConcentric": locationConcentric,
                    "locationRadialHour": locationRadialHour,
                    "locationRadialMinute": locationRadialMinute,
                    "locationDescription": locationDescription,
                },
            )

            # Join with Ranger handles
            self._attachRangeHandlesToIncident(
                incident.eventID,
                incident.number,
                incident.rangerHandles,
                txn,
            )

            # Attach incident types
            self._attachIncidentTypesToIncident(
                incident.eventID,
                incident.number,
                incident.incidentTypes,
                txn,
            )

            # Add report entries
            self._createAndAttachReportEntriesToIncident(
                incident.eventID,
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
            incident=incident,
        )

        self._notifyIncidentUpdate(incident.eventID, incident.number)

        return incident

    async def createIncident(self, incident: Incident, author: str) -> Incident:
        """
        See :meth:`IMSDataStore.createIncident`.
        """
        return await self._createIncident(incident, author=author, directImport=False)

    async def importIncident(self, incident: Incident) -> None:
        """
        See :meth:`IMSDataStore.importIncident`.
        """
        await self._createIncident(incident, author=None, directImport=True)

    async def _setIncidentAttribute(
        self,
        query: str,
        eventID: str,
        incidentNumber: int,
        attribute: str,
        value: ParameterValue,
        author: str,
    ) -> None:
        autoEntry = self._automaticReportEntry(author, now(), attribute, value)

        def setIncidentAttribute(txn: Transaction) -> None:
            txn.execute(
                query,
                {
                    "eventID": eventID,
                    "incidentNumber": incidentNumber,
                    "value": value,
                },
            )

            # Add automatic report entry
            self._createAndAttachReportEntriesToIncident(
                eventID,
                incidentNumber,
                (autoEntry,),
                txn,
            )

        try:
            await self.runInteraction(setIncidentAttribute)
        except StorageError as e:
            self._log.critical(
                "Author {author} unable to update incident "
                "{eventID}#{incidentNumber} ({attribute}={value}): {error}",
                query=query,
                eventID=eventID,
                incidentNumber=incidentNumber,
                attribute=attribute,
                value=value,
                author=author,
                error=e,
            )
            raise

        self._log.info(
            "{author} updated incident {eventID}#{incidentNumber}: "
            "{attribute}={value}",
            query=query,
            eventID=eventID,
            incidentNumber=incidentNumber,
            attribute=attribute,
            value=value,
            author=author,
        )

        self._notifyIncidentUpdate(eventID, incidentNumber)

    async def setIncident_priority(
        self,
        eventID: str,
        incidentNumber: int,
        priority: IncidentPriority,
        author: str,
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_priority`.
        """
        await self._setIncidentAttribute(
            self.query.setIncident_priority.text,
            eventID,
            incidentNumber,
            "priority",
            self.asPriorityValue(priority),
            author,
        )

    async def setIncident_state(
        self,
        eventID: str,
        incidentNumber: int,
        state: IncidentState,
        author: str,
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_state`.
        """
        await self._setIncidentAttribute(
            self.query.setIncident_state.text,
            eventID,
            incidentNumber,
            "state",
            self.asIncidentStateValue(state),
            author,
        )

    async def setIncident_summary(
        self, eventID: str, incidentNumber: int, summary: str, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_summary`.
        """
        await self._setIncidentAttribute(
            self.query.setIncident_summary.text,
            eventID,
            incidentNumber,
            "summary",
            summary,
            author,
        )

    async def setIncident_locationName(
        self, eventID: str, incidentNumber: int, name: str, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_locationName`.
        """
        await self._setIncidentAttribute(
            self.query.setIncident_locationName.text,
            eventID,
            incidentNumber,
            "location name",
            name,
            author,
        )

    async def setIncident_locationConcentricStreet(
        self, eventID: str, incidentNumber: int, streetID: str, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_locationConcentricStreet`.
        """
        await self._setIncidentAttribute(
            self.query.setIncident_locationConcentricStreet.text,
            eventID,
            incidentNumber,
            "location concentric street",
            streetID,
            author,
        )

    async def setIncident_locationRadialHour(
        self, eventID: str, incidentNumber: int, hour: int, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_locationRadialHour`.
        """
        await self._setIncidentAttribute(
            self.query.setIncident_locationRadialHour.text,
            eventID,
            incidentNumber,
            "location radial hour",
            hour,
            author,
        )

    async def setIncident_locationRadialMinute(
        self, eventID: str, incidentNumber: int, minute: int, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_locationRadialMinute`.
        """
        await self._setIncidentAttribute(
            self.query.setIncident_locationRadialMinute.text,
            eventID,
            incidentNumber,
            "location radial minute",
            minute,
            author,
        )

    async def setIncident_locationDescription(
        self, eventID: str, incidentNumber: int, description: str, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_locationDescription`.
        """
        await self._setIncidentAttribute(
            self.query.setIncident_locationDescription.text,
            eventID,
            incidentNumber,
            "location description",
            description,
            author,
        )

    async def setIncident_rangers(
        self,
        eventID: str,
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
                {"eventID": eventID, "incidentNumber": incidentNumber},
            )

            self._attachRangeHandlesToIncident(
                eventID, incidentNumber, rangerHandles, txn
            )

            # Add automatic report entry
            self._createAndAttachReportEntriesToIncident(
                eventID,
                incidentNumber,
                (autoEntry,),
                txn,
            )

        try:
            await self.runInteraction(setIncident_rangers)
        except StorageError as e:
            self._log.critical(
                "Author {author} unable to attach Rangers {rangerHandles} to "
                "incident #{incidentNumber} in event {eventID}: {error}",
                author=author,
                rangerHandles=rangerHandles,
                incidentNumber=incidentNumber,
                eventID=eventID,
                error=e,
            )
            raise

        self._log.info(
            "{author} set Rangers for incident {eventID}#{incidentNumber}: "
            "{rangerHandles}",
            author=author,
            eventID=eventID,
            incidentNumber=incidentNumber,
            rangerHandles=rangerHandles,
        )

        self._notifyIncidentUpdate(eventID, incidentNumber)

    async def setIncident_incidentTypes(
        self,
        eventID: str,
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
                {"eventID": eventID, "incidentNumber": incidentNumber},
            )

            self._attachIncidentTypesToIncident(
                eventID, incidentNumber, incidentTypes, txn
            )

            # Add automatic report entry
            self._createAndAttachReportEntriesToIncident(
                eventID,
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
                "{eventID}: {error}",
                author=author,
                incidentTypes=incidentTypes,
                incidentNumber=incidentNumber,
                eventID=eventID,
                error=e,
            )
            raise

        self._log.info(
            "{author} set incident types for incident "
            "{eventID}#{incidentNumber}: {incidentTypes}",
            author=author,
            eventID=eventID,
            incidentNumber=incidentNumber,
            incidentTypes=incidentTypes,
        )

        self._notifyIncidentUpdate(eventID, incidentNumber)

    async def addReportEntriesToIncident(
        self,
        eventID: str,
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
                raise ValueError(f"Report entry {reportEntry} has author != {author}")

        def addReportEntriesToIncident(txn: Transaction) -> None:
            self._createAndAttachReportEntriesToIncident(
                eventID, incidentNumber, reportEntries, txn
            )

        try:
            await self.runInteraction(addReportEntriesToIncident)
        except StorageError as e:
            self._log.critical(
                "Author {author} unable to create report entries "
                "{reportEntries} to incident "
                "{eventID}#{incidentNumber}: {error}",
                author=author,
                reportEntries=reportEntries,
                incidentNumber=incidentNumber,
                eventID=eventID,
                error=e,
            )
            raise

        self._notifyIncidentUpdate(eventID, incidentNumber)

    ###
    # Field Reports
    ###

    def _fetchFieldReports(
        self, txn: Transaction, eventID: str, excludeSystemEntries: bool
    ) -> Iterable[FieldReport]:
        parameters: Parameters = {
            "eventID": eventID,
            # generated value less than or equal to
            "generatedLTE": 0 if excludeSystemEntries else 1,
        }

        txn.execute(self.query.fieldReports_reportEntries.text, parameters)

        # field report number -> report entry
        reports = defaultdict[int, list[ReportEntry]](list)
        for row in txn.fetchall():
            fieldReportNumber = cast(int, row["FIELD_REPORT_NUMBER"])
            reports[fieldReportNumber].append(
                ReportEntry(
                    created=self.fromDateTimeValue(row["CREATED"]),
                    author=cast(str, row["AUTHOR"]),
                    automatic=bool(row["GENERATED"]),
                    text=cast(str, row["TEXT"]),
                ),
            )

        results = list[FieldReport]()
        txn.execute(self.query.fieldReports.text, parameters)
        for row in txn.fetchall():
            fieldReportNumber = cast(int, row["NUMBER"])
            results.append(
                FieldReport(
                    eventID=eventID,
                    number=fieldReportNumber,
                    created=self.fromDateTimeValue(row["CREATED"]),
                    summary=cast(Optional[str], row["SUMMARY"]),
                    incidentNumber=cast(Optional[int], row["INCIDENT_NUMBER"]),
                    reportEntries=cast(
                        Iterable[ReportEntry], reports[fieldReportNumber]
                    ),
                )
            )

        return tuple[FieldReport, ...](r for r in results)

    def _fetchFieldReport(
        self, txn: Transaction, eventID: str, fieldReportNumber: int
    ) -> FieldReport:
        parameters: Parameters = {
            "eventID": eventID,
            "fieldReportNumber": fieldReportNumber,
        }

        def notFound() -> NoReturn:
            raise NoSuchFieldReportError(f"No field report #{fieldReportNumber}")

        try:
            txn.execute(self.query.fieldReport.text, parameters)
        except OverflowError:
            notFound()

        row = txn.fetchone()
        if row is None:
            notFound()

        txn.execute(self.query.fieldReport_reportEntries.text, parameters)

        reportEntries = tuple(
            ReportEntry(
                created=self.fromDateTimeValue(row["CREATED"]),
                author=cast(str, row["AUTHOR"]),
                automatic=bool(row["GENERATED"]),
                text=cast(str, row["TEXT"]),
            )
            for row in txn.fetchall()
        )

        return FieldReport(
            eventID=eventID,
            number=fieldReportNumber,
            created=self.fromDateTimeValue(row["CREATED"]),
            summary=cast(Optional[str], row["SUMMARY"]),
            incidentNumber=cast(Optional[int], row["INCIDENT_NUMBER"]),
            reportEntries=cast(Iterable[ReportEntry], reportEntries),
        )

    def _fetchFieldReportNumbers(self, txn: Transaction, eventID: str) -> Iterable[int]:
        txn.execute(self.query.fieldReportNumbers.text, {"eventID": eventID})
        return (cast(int, row["NUMBER"]) for row in txn.fetchall())

    async def fieldReports(
        self, eventID: str, excludeSystemEntries: bool = False
    ) -> Iterable[FieldReport]:
        """
        See :meth:`IMSDataStore.fieldReports`.
        """

        def fieldReports(txn: Transaction) -> Iterable[FieldReport]:
            return self._fetchFieldReports(
                txn, eventID, excludeSystemEntries=excludeSystemEntries
            )

        try:
            return await self.runInteraction(fieldReports)
        except NoSuchFieldReportError:
            raise
        except StorageError as e:
            self._log.critical(
                "Unable to look up field reports: {error}",
                error=e,
            )
            raise

    async def fieldReportWithNumber(self, eventID: str, number: int) -> FieldReport:
        """
        See :meth:`IMSDataStore.fieldReportWithNumber`.
        """

        def fieldReportWithNumber(txn: Transaction) -> FieldReport:
            return self._fetchFieldReport(txn, eventID, number)

        try:
            return await self.runInteraction(fieldReportWithNumber)
        except StorageError as e:
            self._log.critical(
                "Unable to look up field report #{number}: {error}",
                number=number,
                error=e,
            )
            raise

    def _nextFieldReportNumber(self, eventID: str, txn: Transaction) -> int:
        """
        Look up the next available field report number.
        """
        txn.execute(self.query.maxFieldReportNumber.text, {"eventID": eventID})
        row = txn.fetchone()
        assert row is not None
        number = cast(Optional[int], row["max(NUMBER)"])
        if number is None:
            return 1
        return number + 1

    def _createAndAttachReportEntriesToFieldReport(
        self,
        eventID: str,
        fieldReportNumber: int,
        reportEntries: Iterable[ReportEntry],
        txn: Transaction,
    ) -> None:
        reportEntries = tuple(reportEntries)

        for reportEntry in reportEntries:
            self._createReportEntry(reportEntry, txn)

            # Join to incident
            txn.execute(
                self.query.attachReportEntryToFieldReport.text,
                {
                    "eventID": eventID,
                    "fieldReportNumber": fieldReportNumber,
                    "reportEntryID": txn.lastrowid,
                },
            )

        self._log.info(
            "Attached report entries to field report "
            "{eventID}#{fieldReportNumber}: {reportEntries}",
            storeWriteClass=FieldReport,
            eventID=eventID,
            fieldReportNumber=fieldReportNumber,
            reportEntries=reportEntries,
        )

    async def _createFieldReport(
        self,
        fieldReport: FieldReport,
        author: str | None,
        directImport: bool,
    ) -> FieldReport:
        if directImport:
            if author is not None:
                raise ValueError("Field report author may not be specified.")
            if fieldReport.number <= 0:
                raise ValueError("Field report number must be greater than zero.")
        else:
            if not author:
                raise ValueError("Field report author is required.")
            if fieldReport.number != 0:
                raise ValueError("Field report number must be zero.")

            for reportEntry in fieldReport.reportEntries:
                assert not reportEntry.automatic

            # Add initial report entries
            reportEntries = tuple(self._initialReportEntries(fieldReport, author))
            fieldReport = fieldReport.replace(
                reportEntries=(reportEntries + tuple(fieldReport.reportEntries))
            )

        def createFieldReport(
            txn: Transaction, fieldReport: FieldReport = fieldReport
        ) -> FieldReport:
            if not directImport:
                # Assign the incident number a number
                number = self._nextFieldReportNumber(fieldReport.eventID, txn)
                fieldReport = fieldReport.replace(number=number)

            # Write incident row
            created = self.asDateTimeValue(fieldReport.created)
            txn.execute(
                self.query.createFieldReport.text,
                {
                    "eventID": fieldReport.eventID,
                    "fieldReportNumber": fieldReport.number,
                    "fieldReportCreated": created,
                    "fieldReportSummary": fieldReport.summary,
                    "incidentNumber": fieldReport.incidentNumber,
                },
            )

            # Add report entries
            self._createAndAttachReportEntriesToFieldReport(
                fieldReport.eventID,
                fieldReport.number,
                fieldReport.reportEntries,
                txn,
            )

            return fieldReport

        try:
            fieldReport = await self.runInteraction(createFieldReport)
        except StorageError as e:
            self._log.critical(
                "Unable to create field report {fieldReport}: {error}",
                fieldReport=fieldReport,
                author=author,
                error=e,
            )
            raise

        self._log.info(
            "Created field report: {fieldReport}",
            storeWriteClass=FieldReport,
            fieldReport=fieldReport,
        )

        return fieldReport

    async def createFieldReport(
        self, fieldReport: FieldReport, author: str
    ) -> FieldReport:
        """
        See :meth:`IMSDataStore.createFieldReport`.
        """
        return await self._createFieldReport(
            fieldReport, author=author, directImport=False
        )

    async def importFieldReport(self, fieldReport: FieldReport) -> None:
        """
        See :meth:`IMSDataStore.importFieldReport`.
        """
        await self._createFieldReport(fieldReport, author=None, directImport=True)

    async def _setFieldReportAttribute(
        self,
        query: str,
        eventID: str,
        fieldReportNumber: int,
        attribute: str,
        value: ParameterValue,
        author: str,
    ) -> None:
        autoEntry = self._automaticReportEntry(author, now(), attribute, value)

        def setFieldReportAttribute(txn: Transaction) -> None:
            txn.execute(
                query,
                {
                    "eventID": eventID,
                    "fieldReportNumber": fieldReportNumber,
                    "value": value,
                },
            )

            # Add report entries
            self._createAndAttachReportEntriesToFieldReport(
                eventID,
                fieldReportNumber,
                (autoEntry,),
                txn,
            )

        try:
            await self.runInteraction(setFieldReportAttribute)
        except StorageError as e:
            self._log.critical(
                "Author {author} unable to update field report "
                "{eventID}#{fieldReportNumber} "
                "({attribute}={value}): {error}",
                query=query,
                eventID=eventID,
                fieldReportNumber=fieldReportNumber,
                attribute=attribute,
                value=value,
                author=author,
                error=e,
            )
            raise

        self._log.info(
            "{author} updated field report #{fieldReportNumber}: "
            "{attribute}={value}",
            storeWriteClass=FieldReport,
            query=query,
            eventID=eventID,
            fieldReportNumber=fieldReportNumber,
            attribute=attribute,
            value=value,
            author=author,
        )

    async def setFieldReport_summary(
        self,
        eventID: str,
        fieldReportNumber: int,
        summary: str,
        author: str,
    ) -> None:
        """
        See :meth:`IMSDataStore.setFieldReport_summary`.
        """
        await self._setFieldReportAttribute(
            self.query.setFieldReport_summary.text,
            eventID,
            fieldReportNumber,
            "summary",
            summary,
            author,
        )

    async def addReportEntriesToFieldReport(
        self,
        eventID: str,
        fieldReportNumber: int,
        reportEntries: Iterable[ReportEntry],
        author: str,
    ) -> None:
        """
        See :meth:`IMSDataStore.addReportEntriesToFieldReport`.
        """
        reportEntries = tuple(reportEntries)

        for reportEntry in reportEntries:
            if reportEntry.automatic:
                raise ValueError(
                    f"Automatic report entry {reportEntry} may not be created "
                    f"by user {author}"
                )

            if reportEntry.author != author:
                raise ValueError(f"Report entry {reportEntry} has author != {author}")

        def addReportEntriesToFieldReport(txn: Transaction) -> None:
            self._createAndAttachReportEntriesToFieldReport(
                eventID, fieldReportNumber, reportEntries, txn
            )

        try:
            await self.runInteraction(addReportEntriesToFieldReport)
        except StorageError as e:
            self._log.critical(
                "Author {author} unable to create report entries "
                "{reportEntries} to field report "
                "{eventID}#{fieldReportNumber}: {error}",
                author=author,
                reportEntries=reportEntries,
                fieldReportNumber=fieldReportNumber,
                eventID=eventID,
                error=e,
            )
            raise

    ###
    # Incident to Field Report Relationships
    ###

    def _fetchDetachedFieldReportNumbers(
        self, txn: Transaction, eventID: str
    ) -> Iterable[int]:
        txn.execute(
            self.query.detachedFieldReportNumbers.text,
            {"eventID": eventID},
        )
        return (cast(int, row["NUMBER"]) for row in txn.fetchall())

    def _fetchAttachedFieldReportNumbers(
        self, txn: Transaction, eventID: str, incidentNumber: int
    ) -> Iterable[int]:
        txn.execute(
            self.query.attachedFieldReportNumbers.text,
            {"eventID": eventID, "incidentNumber": incidentNumber},
        )
        return (cast(int, row["NUMBER"]) for row in txn.fetchall())

    async def fieldReportsAttachedToIncident(
        self, eventID: str, incidentNumber: int
    ) -> Iterable[FieldReport]:
        """
        See :meth:`IMSDataStore.attachedFieldReports`.
        """

        def fieldReportsAttachedToIncident(
            txn: Transaction,
        ) -> Iterable[FieldReport]:
            return tuple(
                self._fetchFieldReport(txn, eventID, number)
                for number in tuple(
                    self._fetchAttachedFieldReportNumbers(txn, eventID, incidentNumber)
                )
            )

        try:
            return await self.runInteraction(fieldReportsAttachedToIncident)
        except StorageError as e:
            self._log.critical(
                "Unable to look up field reports attached to incident "
                "#{incidentNumber} in event {eventID}: {error}",
                incidentNumber=incidentNumber,
                eventID=eventID,
                error=e,
            )
            raise

    async def attachFieldReportToIncident(
        self,
        fieldReportNumber: int,
        eventID: str,
        incidentNumber: int,
        author: str,
    ) -> None:
        """
        See :meth:`IMSDataStore.attachFieldReportToIncident`.
        """
        await self._setFieldReportAttribute(
            self.query.attachFieldReportToIncident.text,
            eventID,
            fieldReportNumber,
            "incident_number",
            incidentNumber,
            author,
        )

    async def detachFieldReportFromIncident(
        self,
        fieldReportNumber: int,
        eventID: str,
        incidentNumber: int,
        author: str,
    ) -> None:
        """
        See :meth:`IMSDataStore.detachFieldReportFromIncident`.
        """
        await self._setFieldReportAttribute(
            self.query.attachFieldReportToIncident.text,
            eventID,
            fieldReportNumber,
            "incident_number",
            None,
            author,
        )


@frozen(kw_only=True)
class DatabaseManager:
    """
    Generic manager for databases.
    """

    _log: ClassVar[Logger] = Logger()

    store: DatabaseStore

    async def upgradeSchema(self, targetVersion: int | None = None) -> bool:
        """
        Apply schema updates
        """
        if targetVersion is None:
            latestVersion = self.store.schemaVersion
        else:
            latestVersion = targetVersion

        currentVersion = await self.store.dbSchemaVersion()

        if currentVersion < 0:
            raise StorageError(f"No upgrade path from schema version {currentVersion}")

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
                except FileNotFoundError as e:
                    self._log.critical(
                        "Unable to upgrade schema in store {store.__class__} "
                        "from {fromVersion} to {toVersion} "
                        "due to missing schema upgrade file",
                        store=self.store,
                        fromVersion=fromVersion,
                        toVersion=toVersion,
                    )
                    raise StorageError("schema upgrade file not found") from e
                await self.store.applySchema(sql)
            except StorageError as e:
                raise StorageError(
                    f"Unable to upgrade schema from "
                    f"{fromVersion} to {toVersion}: {e}"
                ) from e

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
