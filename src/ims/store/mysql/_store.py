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
Incident Management System SQL data store.
"""

from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Iterator, Mapping, Optional, Tuple, Union, cast

from attr import Factory, attrib, attrs
from attr.validators import instance_of, optional

from pymysql.cursors import DictCursor as Cursor
from pymysql.err import MySQLError

from twisted.enterprise.adbapi import ConnectionPool
from twisted.logger import Logger

from ims.model import (
    Event, Incident, IncidentPriority, IncidentReport, IncidentState,
    ReportEntry,
)

from .._db import DatabaseStore, Query
from .._exceptions import StorageError


__all__ = ()


ParameterValue = Optional[Union[bytes, str, int, float]]
Parameters = Mapping[str, ParameterValue]

Row = Parameters
Rows = Iterator[Row]

query_eventID = "select ID from EVENT where NAME = %(eventID)s"



@attrs(frozen=True)
class DataStore(DatabaseStore):
    """
    Incident Management System MySQL data store.
    """

    _log = Logger()

    schemaVersion = 2
    schemaBasePath = Path(__file__).parent / "schema"
    sqlFileExtension = "mysql"


    @attrs(frozen=False)
    class _State(object):
        """
        Internal mutable state for :class:`DataStore`.
        """

        db: Optional[ConnectionPool] = attrib(
            validator=optional(instance_of(ConnectionPool)),
            default=None, init=False,
        )


    hostName: str = attrib(validator=instance_of(str))
    hostPort: str = attrib(validator=instance_of(int))
    database: str = attrib(validator=instance_of(str))
    username: str = attrib(validator=instance_of(str))
    password: str = attrib(validator=instance_of(str))

    _state: _State = attrib(default=Factory(_State), init=False)


    @property
    def _db(self) -> ConnectionPool:
        if self._state.db is None:
            db = ConnectionPool(
                "pymysql",
                host=self.hostName,
                port=self.hostPort,
                database=self.database,
                user=self.username,
                password=self.password,
                cursorclass=Cursor,
                cp_reconnect=True,
            )

            # self._upgradeSchema(db)

            self._state.db = db

        return self._state.db


    async def runQuery(
        self, query: Query, params: Optional[Parameters] = None
    ) -> Rows:
        if params is None:
            params = {}

        try:
            return iter(await self._db.runQuery(query.text, params))

        except MySQLError as e:
            self._log.critical(
                "Unable to {description}: {error}",
                description=query.description, error=e,
            )
            raise StorageError(e)


    async def runOperation(
        self, query: Query, params: Optional[Parameters] = None
    ) -> None:
        if params is None:
            params = {}

        try:
            await self._db.runOperation(query.text, params)

        except MySQLError as e:
            self._log.critical(
                "Unable to {description}: {error}",
                description=query.description, error=e,
            )
            raise StorageError(e)


    async def reconnect(self) -> None:
        """
        See :meth:`DatabaseStore.reconnect`.
        """
        self._state.db = None


    async def dbSchemaVersion(self) -> int:
        """
        See `meth:DatabaseStore.dbSchemaVersion`.
        """
        query = self._query_schemaVersion

        try:
            rows: Rows = iter(await self._db.runQuery(query.text))
            try:
                row = next(rows)
            except StopIteration:
                raise StorageError("Invalid schema: no version")
            return cast(int, row["VERSION"])

        except MySQLError as e:
            message = e.args[1]
            if (
                message.startswith("Table '") and
                message.endswith(".SCHEMA_INFO' doesn't exist")
            ):
                return 0

            self._log.critical(
                "Unable to {description}: {error}",
                description=query.description, error=e,
            )
            raise StorageError(e)

    _query_schemaVersion = Query(
        "look up schema version",
        """
        select VERSION from SCHEMA_INFO
        """
    )


    async def applySchema(self, sql: str) -> None:
        """
        See :meth:`IMSDataStore.applySchema`.
        """
        def applySchema(txn: Cursor) -> None:
            # FIXME: OMG this is gross but works for now
            for statement in sql.split(";"):
                statement = statement.strip()
                if statement and not statement.startswith("--"):
                    txn.execute(statement)

        try:
            await self._db.runInteraction(applySchema)
        except MySQLError as e:
            self._log.critical(
                "Unable to apply schema: {error}", sql=sql, error=e
            )
            raise StorageError(f"Unable to apply schema: {e}")


    async def validate(self) -> None:
        """
        See :meth:`IMSDataStore.validate`.
        """
        self._log.info("Validating data store...")

        valid = True

        if not valid:
            raise StorageError("Data store validation failed")


    ###
    # Events
    ###


    async def events(self) -> Iterable[Event]:
        """
        See :meth:`IMSDataStore.events`.
        """
        rows = await self.runQuery(self._query_events)
        return (Event(id=cast(str, row["NAME"])) for row in rows)

    _query_events = Query(
        "look up events",
        """
        select NAME from EVENT
        """
    )


    async def createEvent(self, event: Event) -> None:
        """
        See :meth:`IMSDataStore.createEvent`.
        """
        await self.runOperation(
            self._query_createEvent, dict(eventID=event.id)
        )

    _query_createEvent = Query(
        "create event",
        """
        insert into EVENT (NAME) values (%(eventID)s)
        """
    )


    async def _eventAccess(self, event: Event, mode: str) -> Iterable[str]:
        rows = await self.runQuery(
            self._query_eventAccess, dict(eventID=event.id, mode=mode)
        )
        return (cast(str, row["EXPRESSION"]) for row in rows)

    _query_eventAccess = Query(
        "look up event access",
        f"""
        select EXPRESSION from EVENT_ACCESS
        where EVENT = ({query_eventID}) and MODE = %(mode)s
        """
    )


    async def _setEventAccess(
        self, event: Event, mode: str, expressions: Iterable[str]
    ) -> None:
        expressions = tuple(expressions)

        def setEventAccess(txn: Cursor) -> None:
            txn.execute(
                self._query_clearEventAccessForMode.text,
                dict(eventID=event.id, mode=mode),
            )
            for expression in expressions:
                txn.execute(
                    self._query_clearEventAccessForExpression.text,
                    dict(eventID=event.id, expression=expression),
                )
                txn.execute(
                    self._query_addEventAccess.text, dict(
                        eventID=event.id,
                        expression=expression,
                        mode=mode,
                    )
                )

        try:
            await self._db.runInteraction(setEventAccess)
        except MySQLError as e:
            self._log.critical(
                "Unable to set access for {event} to {mode} "
                "for {expressions}: {error}",
                event=event, mode=mode, expressions=expressions, error=e
            )
            raise StorageError(f"Unable to set event access: {e}")

    _query_clearEventAccessForMode = Query(
        "clear event access for mode",
        f"""
        delete from EVENT_ACCESS
        where EVENT = ({query_eventID}) and MODE = %(mode)s
        """
    )

    _query_clearEventAccessForExpression = Query(
        "clear event access for expression",
        f"""
        delete from EVENT_ACCESS
        where EVENT = ({query_eventID}) and EXPRESSION = %(expression)s
        """
    )

    _query_addEventAccess = Query(
        "add event access",
        f"""
        insert into EVENT_ACCESS (EVENT, EXPRESSION, MODE)
        values (({query_eventID}), %(expression)s, %(mode)s)
        """
    )


    async def readers(self, event: Event) -> Iterable[str]:
        """
        See :meth:`IMSDataStore.readers`.
        """
        return await self._eventAccess(event, "read")


    async def setReaders(self, event: Event, readers: Iterable[str]) -> None:
        """
        See :meth:`IMSDataStore.setReaders`.
        """
        return await self._setEventAccess(event, "read", readers)


    async def writers(self, event: Event) -> Iterable[str]:
        """
        See :meth:`IMSDataStore.writers`.
        """
        return await self._eventAccess(event, "write")


    async def setWriters(self, event: Event, writers: Iterable[str]) -> None:
        """
        See :meth:`IMSDataStore.setWriters`.
        """
        return await self._setEventAccess(event, "write", writers)


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

        rows = await self.runQuery(query)
        return (cast(str, row["NAME"]) for row in rows)

    _query_incidentTypes = Query(
        "look up incident types",
        """
        select NAME from INCIDENT_TYPE
        """
    )

    _query_incidentTypesNotHidden = Query(
        "look up non-hidden incident types",
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
        await self.runOperation(
            self._query_createIncidentType,
            dict(incidentType=incidentType, hidden=hidden),
        )

        self._log.info(
            "Created incident type: {incidentType} (hidden={hidden})",
            incidentType=incidentType, hidden=hidden,
        )

    _query_createIncidentType = Query(
        "create incident type",
        """
        insert into INCIDENT_TYPE (NAME, HIDDEN)
        values (%(incidentType)s, %(hidden)s)
        """
    )


    async def _hideShowIncidentTypes(
        self, incidentTypes: Iterable[str], hidden: bool
    ) -> None:
        incidentTypes = tuple(incidentTypes)

        def hideShowIncidentTypes(txn: Cursor) -> None:
            for incidentType in incidentTypes:
                txn.execute(
                    self._query_hideShowIncidentType.text,
                    dict(incidentType=incidentType, hidden=hidden),
                )

        try:
            await self._db.runInteraction(hideShowIncidentTypes)
        except MySQLError as e:
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


    _query_hideShowIncidentType = Query(
        "hide/show incident type",
        """
        update INCIDENT_TYPE set HIDDEN = %(hidden)s
        where NAME = %(incidentType)s
        """
    )


    async def showIncidentTypes(self, incidentTypes: Iterable[str]) -> None:
        """
        See :meth:`IMSDataStore.showIncidentTypes`.
        """
        return await self._hideShowIncidentTypes(incidentTypes, False)


    async def hideIncidentTypes(self, incidentTypes: Iterable[str]) -> None:
        """
        See :meth:`IMSDataStore.hideIncidentTypes`.
        """
        return await self._hideShowIncidentTypes(incidentTypes, True)


    ###
    # Concentric Streets
    ###


    async def concentricStreets(self, event: Event) -> Mapping[str, str]:
        """
        See :meth:`IMSDataStore.concentricStreets`.
        """
        rows = await self.runQuery(
            self._query_concentricStreets, dict(eventID=event.id)
        )
        return MappingProxyType(dict(
            (cast(str, row["ID"]), cast(str, row["NAME"])) for row in rows
        ))

    _query_concentricStreets = Query(
        "look up concentric streets",
        f"""
        select ID, NAME from CONCENTRIC_STREET where EVENT = ({query_eventID})
        """
    )


    async def createConcentricStreet(
        self, event: Event, id: str, name: str
    ) -> None:
        """
        See :meth:`IMSDataStore.createConcentricStreet`.
        """
        await self.runOperation(
            self._query_createConcentricStreet,
            dict(eventID=event.id, streetID=id, streetName=name)
        )

        self._log.info(
            "Created concentric street in {event}: {streetName}",
            storeWriteClass=Event, event=event, concentricStreetName=name,
        )

    _query_createConcentricStreet = Query(
        "create concentric street",
        f"""
        insert into CONCENTRIC_STREET (EVENT, ID, NAME)
        values (({query_eventID}), %(streetID)s, %(streetName)s)
        """
    )


    ###
    # Incidents
    ###


    async def incidents(self, event: Event) -> Iterable[Incident]:
        """
        See :meth:`IMSDataStore.incidents`.
        """
        raise NotImplementedError("incidents()")


    async def incidentWithNumber(self, event: Event, number: int) -> Incident:
        """
        See :meth:`IMSDataStore.incidentWithNumber`.
        """
        raise NotImplementedError("incidentWithNumber()")


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
