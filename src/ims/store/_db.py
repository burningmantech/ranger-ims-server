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

from abc import ABC, abstractmethod
from pathlib import Path
from textwrap import dedent
from types import MappingProxyType
from typing import Callable, Iterable, Iterator, Mapping, Optional, Union, cast

from attr import attrib, attrs
from attr.validators import instance_of

from twisted.logger import Logger

from ims.model import Event

from ._abc import IMSDataStore
from ._exceptions import StorageError


__all__ = ()


ParameterValue = Optional[Union[bytes, str, int, float]]
Parameters = Mapping[str, ParameterValue]

Row = Parameters
Rows = Iterator[Row]



@attrs(frozen=True)
class Query(object):
    description: str = attrib(validator=instance_of(str))
    text: str = attrib(validator=instance_of(str), converter=dedent)



def _queryAttribute() -> Query:
    return attrib(validator=instance_of(Query))



@attrs(frozen=True)
class Queries(object):
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



class Cursor(ABC):
    @abstractmethod
    def execute(
        self, sql: str, parameters: Optional[Parameters] = None
    ) -> "Cursor":
        """
        Executes an SQL statement.
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
    async def runInteraction(self, interaction: Callable) -> None:
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


    ###
    # Events
    ###


    async def events(self) -> Iterable[Event]:
        """
        See :meth:`IMSDataStore.events`.
        """
        return (
            Event(id=row["name"])
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
            raise StorageError(e)

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
            cast(str, row["name"]) for row in await self.runQuery(query)
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
