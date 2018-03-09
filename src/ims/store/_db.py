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
from collections.abc import Iterable as IterableABC
from datetime import datetime as DateTime, timezone as TimeZone
from pathlib import Path
from textwrap import dedent
from types import MappingProxyType
from typing import (
    Callable, Iterable, Iterator, Mapping, Optional, Tuple, TypeVar, Union,
    cast,
)

from attr import attrib, attrs
from attr.validators import instance_of

from twisted.logger import Logger

from ims.model import (
    Event, Incident, IncidentPriority, IncidentReport, IncidentState,
    Location, ReportEntry, RodGarettAddress,
)

from ._abc import IMSDataStore
from ._exceptions import NoSuchIncidentError, StorageError


__all__ = ()


ParameterValue = Optional[Union[bytes, str, int, float]]
Parameters = Mapping[str, ParameterValue]

Row = Parameters
Rows = Iterator[Row]

T = TypeVar("T")


@attrs(frozen=True)
class Query(object):
    description: str = attrib(validator=instance_of(str))
    text: str = attrib(validator=instance_of(str), converter=dedent)



def _queryAttribute() -> Query:
    return attrib(validator=instance_of(Query))



@attrs(frozen=True)
class Queries(object):
    schemaVersion                        = _queryAttribute()
    events                               = _queryAttribute()
    createEvent                          = _queryAttribute()
    eventAccess                          = _queryAttribute()
    clearEventAccessForMode              = _queryAttribute()
    clearEventAccessForExpression        = _queryAttribute()
    addEventAccess                       = _queryAttribute()
    incidentTypes                        = _queryAttribute()
    incidentTypesNotHidden               = _queryAttribute()
    createIncidentType                   = _queryAttribute()
    hideShowIncidentType                 = _queryAttribute()
    concentricStreets                    = _queryAttribute()
    createConcentricStreet               = _queryAttribute()
    detachedReportEntries                = _queryAttribute()
    incident                             = _queryAttribute()
    incident_rangers                     = _queryAttribute()
    incident_incidentTypes               = _queryAttribute()
    incident_reportEntries               = _queryAttribute()
    incidentNumbers                      = _queryAttribute()
    maxIncidentNumber                    = _queryAttribute()
    attachRangeHandleToIncident          = _queryAttribute()
    attachIncidentTypeToIncident         = _queryAttribute()
    createReportEntry                    = _queryAttribute()
    attachReportEntryToIncident          = _queryAttribute()
    createIncident                       = _queryAttribute()
    setIncident_priority                 = _queryAttribute()
    setIncident_state                    = _queryAttribute()
    setIncident_summary                  = _queryAttribute()
    setIncident_locationName             = _queryAttribute()
    setIncident_locationConcentricStreet = _queryAttribute()
    setIncident_locationRadialHour       = _queryAttribute()
    setIncident_locationRadialMinute     = _queryAttribute()
    setIncident_locationDescription      = _queryAttribute()
    clearIncidentRangers                 = _queryAttribute()
    clearIncidentIncidentTypes           = _queryAttribute()
    incidentReport                       = _queryAttribute()
    incidentReport_reportEntries         = _queryAttribute()
    incidentReportNumbers                = _queryAttribute()
    maxIncidentReportNumber              = _queryAttribute()
    createIncidentReport                 = _queryAttribute()
    attachReportEntryToIncidentReport    = _queryAttribute()
    setIncidentReport_summary            = _queryAttribute()
    detachedIncidentReportNumbers        = _queryAttribute()
    attachedIncidentReportNumbers        = _queryAttribute()
    incidentsAttachedToIncidentReport    = _queryAttribute()
    attachIncidentReportToIncident       = _queryAttribute()
    detachIncidentReportFromIncident     = _queryAttribute()



class Cursor(IterableABC):
    @abstractmethod
    def execute(
        self, sql: str, parameters: Optional[Parameters] = None
    ) -> "Cursor":
        """
        Executes an SQL statement.
        """


    @abstractmethod
    def fetchone(self) -> Row:
        """
        Fetch the next row.
        """



class DatabaseStore(IMSDataStore):
    """
    Incident Management System data store using a managed database.
    """

    _log = Logger()

    schemaVersion = 0
    schemaBasePath = Path(__file__).parent / "schema"
    sqlFileExtension = "sql"

    query: Queries


    @classmethod
    def loadSchema(cls, version: Union[int, str] = None) -> str:
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
        return DatabaseManager(self)


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
    async def runInteraction(self, interaction: Callable[[Cursor], T]) -> T:
        """
        Create a cursor and call the given interaction with the cursor as the
        sole argument.
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


    async def upgradeSchema(self) -> None:
        """
        See :meth:`IMSDataStore.upgradeSchema`.
        """
        if await self.dbManager.upgradeSchema():
            await self.disconnect()


    @abstractmethod
    def asIncidentStateValue(
        self, incidentState: IncidentState
    ) -> ParameterValue:
        """
        Convert an :class:`IncidentState` to a state value for the database.
        """


    @abstractmethod
    def fromIncidentStateValue(self, value: ParameterValue) -> IncidentState:
        """
        Convert a state value from the database to an :class:`IncidentState`.
        """


    @abstractmethod
    def asIncidentPriorityValue(
        self, incidentPriority: IncidentPriority
    ) -> ParameterValue:
        """
        Convert an :class:`IncidentPriority` to an incident priority value for
        the database.
        """


    @abstractmethod
    def fromIncidentPriorityValue(
        self, value: ParameterValue
    ) -> IncidentPriority:
        """
        Convert an incident priority value from the database to an
        :class:`IncidentPriority`.
        """


    @abstractmethod
    def asDateTimeValue(self, dateTime: DateTime) -> ParameterValue:
        """
        Convert a :class:`DateTime` to a date-time value for the database.
        """


    @abstractmethod
    def fromDateTimeValue(self, value: ParameterValue) -> DateTime:
        """
        Convert a date-time value from the database to a :class:`DateTime`.
        """


    ###
    # Events
    ###


    async def events(self) -> Iterable[Event]:
        """
        See :meth:`IMSDataStore.events`.
        """
        return (
            Event(id=row["NAME"])
            for row in await self.runQuery(self.query.events)
        )


    async def createEvent(self, event: Event) -> None:
        """
        See :meth:`IMSDataStore.createEvent`.
        """
        await self.runOperation(
            self.query.createEvent, dict(eventID=event.id)
        )

        self._log.info(
            "Created event: {event}", storeWriteClass=Event, event=event,
        )


    async def _eventAccess(self, event: Event, mode: str) -> Iterable[str]:
        return (
            cast(str, row["EXPRESSION"]) for row in await self.runQuery(
                self.query.eventAccess, dict(eventID=event.id, mode=mode)
            )
        )


    async def _setEventAccess(
        self, event: Event, mode: str, expressions: Iterable[str]
    ) -> None:
        expressions = tuple(expressions)

        def setEventAccess(txn: Cursor) -> None:
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
                    self.query.addEventAccess.text, dict(
                        eventID=event.id,
                        expression=expression,
                        mode=mode,
                    )
                )

        try:
            await self.runInteraction(setEventAccess)
        except StorageError as e:
            self._log.critical(
                "Unable to set {mode} access for {event}: {error}",
                event=event, mode=mode, expressions=expressions, error=e,
            )
            raise

        self._log.info(
            "Set {mode} access for {event}: {expressions}",
            storeWriteClass=Event,
            event=event, mode=mode, expressions=expressions,
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
            query = self.query.incidentTypes
        else:
            query = self.query.incidentTypesNotHidden

        return (
            cast(str, row["NAME"]) for row in await self.runQuery(query)
        )


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
            incidentType=incidentType, hidden=hidden,
        )


    async def _hideShowIncidentTypes(
        self, incidentTypes: Iterable[str], hidden: bool
    ) -> None:
        incidentTypes = tuple(incidentTypes)

        def hideShowIncidentTypes(txn: Cursor) -> None:
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
                incidentTypes=incidentTypes, hidden=hidden,
            )
            raise StorageError(f"Unable to set hidden: {e}")

        self._log.info(
            "Set hidden to {hidden} for incident types: {incidentTypes}",
            incidentTypes=incidentTypes, hidden=hidden,
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
        return MappingProxyType(dict(
            (cast(str, row["ID"]), cast(str, row["NAME"]))
            for row in await self.runQuery(
                self.query.concentricStreets, dict(eventID=event.id)
            )
        ))


    async def createConcentricStreet(
        self, event: Event, id: str, name: str
    ) -> None:
        """
        See :meth:`IMSDataStore.createConcentricStreet`.
        """
        await self.runOperation(
            self.query.createConcentricStreet,
            dict(eventID=event.id, streetID=id, streetName=name)
        )

        self._log.info(
            "Created concentric street in {event}: {streetName}",
            storeWriteClass=Event, event=event, concentricStreetName=name,
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
        def detachedReportEntries(txn: Cursor) -> Iterable[ReportEntry]:
            return tuple(
                ReportEntry(
                    created=self.fromDateTimeValue(row["CREATED"]),
                    author=row["AUTHOR"],
                    automatic=bool(row["GENERATED"]),
                    text=row["TEXT"],
                )
                for row in txn.execute(
                    self.query.detachedReportEntries.text, {}
                ) if row["TEXT"]
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
        self, event: Event, incidentNumber: int, cursor: Cursor
    ) -> Incident:
        parameters: Parameters = dict(
            eventID=event.id, incidentNumber=incidentNumber
        )

        def notFound() -> None:
            raise NoSuchIncidentError(
                f"No incident #{incidentNumber} in event {event}"
            )

        try:
            cursor.execute(self.query.incident.text, parameters)
        except OverflowError:
            notFound()

        row = cursor.fetchone()
        if row is None:
            notFound()

        rangerHandles = tuple(
            row["RANGER_HANDLE"] for row in cursor.execute(
                self.query.incident_rangers.text, parameters
            )
        )

        incidentTypes = tuple(
            row["NAME"]
            for row in cursor.execute(
                self.query.incident_incidentTypes.text, parameters
            )
        )

        reportEntries = tuple(
            ReportEntry(
                created=self.fromDateTimeValue(row["CREATED"]),
                author=row["AUTHOR"],
                automatic=bool(row["GENERATED"]),
                text=row["TEXT"],
            )
            for row in cursor.execute(
                self.query.incident_reportEntries.text, parameters
            ) if row["TEXT"]
        )

        # FIXME: This is because schema thinks concentric is an int
        if row["LOCATION_CONCENTRIC"] is None:
            concentric = None
        else:
            concentric = str(row["LOCATION_CONCENTRIC"])

        return Incident(
            event=event,
            number=incidentNumber,
            created=self.fromDateTimeValue(row["CREATED"]),
            state=self.fromIncidentStateValue(row["STATE"]),
            priority=self.fromIncidentPriorityValue(row["PRIORITY"]),
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


    def _fetchIncidentNumbers(
        self, event: Event, cursor: Cursor
    ) -> Iterable[int]:
        """
        Look up all incident numbers for the given event.
        """
        for row in cursor.execute(
            self.query.incidentNumbers.text, dict(eventID=event.id)
        ):
            yield row["NUMBER"]


    async def incidents(self, event: Event) -> Iterable[Incident]:
        """
        See :meth:`IMSDataStore.incidents`.
        """
        def incidents(txn: Cursor) -> Iterable[Incident]:
            return tuple(
                self._fetchIncident(event, number, txn)
                for number in
                tuple(self._fetchIncidentNumbers(event, txn))
            )

        try:
            return await self.runInteraction(incidents)
        except NoSuchIncidentError:
            raise
        except StorageError as e:
            self._log.critical(
                "Unable to look up incidents in {event}: {error}",
                event=event, error=e,
            )
            raise


    async def incidentWithNumber(self, event: Event, number: int) -> Incident:
        """
        See :meth:`IMSDataStore.incidentWithNumber`.
        """
        def incidentWithNumber(txn: Cursor) -> Incident:
            return self._fetchIncident(event, number, txn)

        try:
            return await self.runInteraction(incidentWithNumber)
        except StorageError as e:
            self._log.critical(
                "Unable to look up incident #{number} in {event}: {error}",
                event=event, number=number, error=e,
            )
            raise


    async def createIncident(
        self, incident: Incident, author: str
    ) -> Incident:
        """
        See :meth:`IMSDataStore.createIncident`.
        """
        raise NotImplementedError("createIncident()")


    async def importIncident(self, incident: Incident) -> None:
        """
        See :meth:`IMSDataStore.importIncident`.
        """
        raise NotImplementedError("importIncident()")


    async def setIncident_priority(
        self, event: Event, incidentNumber: int, priority: IncidentPriority,
        author: str,
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_priority`.
        """
        raise NotImplementedError("setIncident_priority()")


    async def setIncident_state(
        self, event: Event, incidentNumber: int, state: IncidentState,
        author: str,
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_state`.
        """
        raise NotImplementedError("setIncident_state()")


    async def setIncident_summary(
        self, event: Event, incidentNumber: int, summary: str, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_summary`.
        """
        raise NotImplementedError("setIncident_summary()")


    async def setIncident_locationName(
        self, event: Event, incidentNumber: int, name: str, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_locationName`.
        """
        raise NotImplementedError("setIncident_locationName()")


    async def setIncident_locationConcentricStreet(
        self, event: Event, incidentNumber: int, streetID: str, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_locationConcentricStreet`.
        """
        raise NotImplementedError("setIncident_locationConcentricStreet()")


    async def setIncident_locationRadialHour(
        self, event: Event, incidentNumber: int, hour: int, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_locationRadialHour`.
        """
        raise NotImplementedError("setIncident_locationRadialHour()")


    async def setIncident_locationRadialMinute(
        self, event: Event, incidentNumber: int, minute: int, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_locationRadialMinute`.
        """
        raise NotImplementedError("setIncident_locationRadialMinute()")


    async def setIncident_locationDescription(
        self, event: Event, incidentNumber: int, description: str, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_locationDescription`.
        """
        raise NotImplementedError("setIncident_locationDescription()")


    async def setIncident_rangers(
        self, event: Event, incidentNumber: int, rangerHandles: Iterable[str],
        author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_rangers`.
        """
        raise NotImplementedError("setIncident_rangers()")


    async def setIncident_incidentTypes(
        self, event: Event, incidentNumber: int, incidentTypes: Iterable[str],
        author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncident_incidentTypes`.
        """
        raise NotImplementedError("setIncident_incidentTypes()")


    async def addReportEntriesToIncident(
        self, event: Event, incidentNumber: int,
        reportEntries: Iterable[ReportEntry], author: str,
    ) -> None:
        """
        See :meth:`IMSDataStore.addReportEntriesToIncident`.
        """
        raise NotImplementedError("addReportEntriesToIncident()")


    ###
    # Incident Reports
    ###


    async def incidentReports(self) -> Iterable[IncidentReport]:
        """
        See :meth:`IMSDataStore.incidentReports`.
        """
        raise NotImplementedError("incidentReports()")


    async def incidentReportWithNumber(self, number: int) -> IncidentReport:
        """
        See :meth:`IMSDataStore.incidentReportWithNumber`.
        """
        raise NotImplementedError("incidentReportWithNumber()")


    async def createIncidentReport(
        self, incidentReport: IncidentReport, author: str
    ) -> IncidentReport:
        """
        See :meth:`IMSDataStore.createIncidentReport`.
        """
        raise NotImplementedError("createIncidentReport()")


    async def setIncidentReport_summary(
        self, incidentReportNumber: int, summary: str, author: str
    ) -> None:
        """
        See :meth:`IMSDataStore.setIncidentReport_summary`.
        """
        raise NotImplementedError("setIncidentReport_summary()")


    async def addReportEntriesToIncidentReport(
        self, incidentReportNumber: int, reportEntries: Iterable[ReportEntry],
        author: str,
    ) -> None:
        """
        See :meth:`IMSDataStore.addReportEntriesToIncidentReport`.
        """
        raise NotImplementedError("addReportEntriesToIncidentReport()")


    ###
    # Incident to Incident Report Relationships
    ###


    async def detachedIncidentReports(self) -> Iterable[IncidentReport]:
        """
        See :meth:`IMSDataStore.detachedIncidentReports`.
        """
        raise NotImplementedError("detachedIncidentReports()")


    async def incidentReportsAttachedToIncident(
        self, event: Event, incidentNumber: int
    ) -> Iterable[IncidentReport]:
        """
        See :meth:`IMSDataStore.incidentReportsAttachedToIncident`.
        """
        raise NotImplementedError("incidentReportsAttachedToIncident()")


    async def incidentsAttachedToIncidentReport(
        self, incidentReportNumber: int
    ) -> Iterable[Tuple[Event, int]]:
        """
        See :meth:`IMSDataStore.incidentsAttachedToIncidentReport`.
        """
        raise NotImplementedError("incidentsAttachedToIncidentReport()")


    async def attachIncidentReportToIncident(
        self, incidentReportNumber: int, event: Event, incidentNumber: int
    ) -> None:
        """
        See :meth:`IMSDataStore.attachIncidentReportToIncident`.
        """
        raise NotImplementedError("attachIncidentReportToIncident()")


    async def detachIncidentReportFromIncident(
        self, incidentReportNumber: int, event: Event, incidentNumber: int
    ) -> None:
        """
        See :meth:`IMSDataStore.detachIncidentReportFromIncident`.
        """
        raise NotImplementedError("detachIncidentReportFromIncident()")



@attrs(frozen=True)
class DatabaseManager(object):
    """
    Generic manager for databases.
    """

    _log = Logger()


    store: DatabaseStore = attrib(validator=instance_of(DatabaseStore))


    async def upgradeSchema(self) -> bool:
        """
        Apply schema updates
        """
        currentVersion = self.store.schemaVersion
        version = await self.store.dbSchemaVersion()

        if version < 0:
            raise StorageError(
                f"No upgrade path from schema version {version}"
            )

        if version == currentVersion:
            # No upgrade needed
            return False

        if version > currentVersion:
            raise StorageError(
                f"Schema version {version} is too new "
                f"(current version is {currentVersion})"
            )

        async def sqlUpgrade(fromVersion: int, toVersion: int) -> None:
            self._log.info(
                "Upgrading database schema from version {fromVersion} to "
                "version {toVersion}",
                fromVersion=fromVersion, toVersion=toVersion,
            )

            if fromVersion == 0:
                fileID = f"{toVersion}"
            else:
                fileID = f"{toVersion}-from-{fromVersion}"

            sql = self.store.loadSchema(version=fileID)
            await self.store.applySchema(sql)

        fromVersion = version

        while fromVersion < currentVersion:
            if fromVersion == 0:
                toVersion = currentVersion
            else:
                toVersion = fromVersion + 1

            await sqlUpgrade(fromVersion, toVersion)
            fromVersion = await self.store.dbSchemaVersion()

            # Make sure the schema version increased from last version
            if fromVersion <= version:
                raise StorageError(
                    f"Schema upgrade did not increase schema version "
                    f"({fromVersion} <= {version})"
                )
            version = fromVersion

        return True
