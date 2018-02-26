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
from textwrap import dedent
from typing import Iterable, Mapping, Tuple

from attr import Factory, attrib, attrs
from attr.validators import instance_of, optional

from twisted.enterprise.adbapi import ConnectionPool
from twisted.logger import Logger

from ims.model import (
    Event, Incident, IncidentPriority, IncidentReport, IncidentState,
    ReportEntry,
)

from .._db import DatabaseStore
from .._exceptions import StorageError


__all__ = ()


def _query(query: str) -> str:
    return dedent(query)



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

        db: ConnectionPool = attrib(
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
                cp_reconnect=True,
            )

            # self._upgradeSchema(db)

            self._state.db = db

        return self._state.db


    async def reconnect(self) -> None:
        """
        See :meth:`DatabaseStore.reconnect`.
        """
        self._state.db = None


    async def dbSchemaVersion(self) -> int:
        """
        See `meth:DatabaseStore.dbSchemaVersion`.
        """
        raise NotImplementedError()


    async def applySchema(self, sql: str) -> None:
        """
        See :meth:`IMSDataStore.applySchema`.
        """
        raise NotImplementedError()


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
        result = await self._db.runQuery(
            self._query_events, {}, "Unable to look up events"
        )
        self._log.info("XXX: {result}", result=result)
        return (Event(id=row["name"]) for row in result)

    _query_events = _query(
        """
        select NAME from EVENT
        """
    )


    async def createEvent(self, event: Event) -> None:
        """
        See :meth:`IMSDataStore.createEvent`.
        """
        raise NotImplementedError("createEvent()")


    async def readers(self, event: Event) -> Iterable[str]:
        """
        See :meth:`IMSDataStore.readers`.
        """
        raise NotImplementedError("readers()")


    async def setReaders(self, event: Event, readers: Iterable[str]) -> None:
        """
        See :meth:`IMSDataStore.setReaders`.
        """
        raise NotImplementedError("setReaders()")


    async def writers(self, event: Event) -> Iterable[str]:
        """
        See :meth:`IMSDataStore.writers`.
        """
        raise NotImplementedError("writers()")


    async def setWriters(self, event: Event, writers: Iterable[str]) -> None:
        """
        See :meth:`IMSDataStore.setWriters`.
        """
        raise NotImplementedError("setWriters()")


    ###
    # Incident Types
    ###


    async def incidentTypes(
        self, includeHidden: bool = False
    ) -> Iterable[str]:
        """
        See :meth:`IMSDataStore.incidentTypes`.
        """
        raise NotImplementedError("incidentTypes()")


    async def createIncidentType(
        self, incidentType: str, hidden: bool = False
    ) -> None:
        """
        See :meth:`IMSDataStore.createIncidentType`.
        """
        raise NotImplementedError("createIncidentType()")


    async def showIncidentTypes(self, incidentTypes: Iterable[str]) -> None:
        """
        See :meth:`IMSDataStore.showIncidentTypes`.
        """
        raise NotImplementedError("showIncidentTypes()")


    async def hideIncidentTypes(self, incidentTypes: Iterable[str]) -> None:
        """
        See :meth:`IMSDataStore.hideIncidentTypes`.
        """
        raise NotImplementedError("hideIncidentTypes()")


    ###
    # Concentric Streets
    ###


    async def concentricStreets(self, event: Event) -> Mapping[str, str]:
        """
        See :meth:`IMSDataStore.concentricStreets`.
        """
        raise NotImplementedError("concentricStreets()")


    async def createConcentricStreet(
        self, event: Event, id: str, name: str
    ) -> None:
        """
        See :meth:`IMSDataStore.createConcentricStreet`.
        """
        raise NotImplementedError("createConcentricStreet()")


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
