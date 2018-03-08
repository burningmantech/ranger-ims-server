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
Tests for :mod:`ranger-ims-server.store.mysql._store`
"""

from typing import List, Optional, cast

from pymysql.err import MySQLError

from twisted.enterprise.adbapi import ConnectionPool
from twisted.internet.defer import ensureDeferred
from twisted.logger import Logger

from ims.model import Event, Incident, IncidentReport

from .service import MySQLService
from .._store import DataStore
from ...test.base import (
    DataStoreTests as SuperDataStoreTests, TestDataStore as SuperTestDataStore
)


__all__ = ()



class DataStoreTests(SuperDataStoreTests):
    """
    Parent test class.
    """

    log = Logger()

    skip: Optional[str] = None

    mysqlService = MySQLService()


    def setUp(self) -> None:
        async def setUp() -> None:
            self.stores: List[TestDataStore] = []

            await self.mysqlService.start()

        # setUp can't return a coroutine, so convert it to a Deferred
        return ensureDeferred(setUp())


    def tearDown(self) -> None:
        async def tearDown() -> None:
            for store in self.stores:
                await store.disconnect()

        # setUp can't return a coroutine, so convert it to a Deferred
        return ensureDeferred(tearDown())


    async def store(self) -> "TestDataStore":
        service = self.mysqlService

        assert service.host is not None
        assert service.port is not None

        name = await service.createDatabase()

        store = TestDataStore(
            self,
            hostName=service.host,
            hostPort=service.port,
            database=name,
            username=service.user,
            password=service.password,
        )
        await store.upgradeSchema()

        self.stores.append(store)

        return store



class TestDataStore(SuperTestDataStore, DataStore):
    """
    See :class:`SuperTestDataStore`.
    """

    maxIncidentNumber = 4294967295

    exceptionClass = MySQLError


    def __init__(
        self, testCase: DataStoreTests,
        hostName: str,
        hostPort: int,
        database: str,
        username: str,
        password: str,
    ) -> None:
        DataStore.__init__(
            self,
            hostName=hostName, hostPort=hostPort,
            database=database,
            username=username, password=password,
        )
        setattr(self._state, "testCase", testCase)


    @property
    def _db(self) -> ConnectionPool:
        if getattr(self._state, "broken", False):
            self.raiseException()

        return cast(property, DataStore._db).fget(self)


    def bringThePain(self) -> None:
        setattr(self._state, "broken", True)
        assert getattr(self._state, "broken")


    async def storeEvent(self, event: Event) -> None:
        await self._db.runOperation(
            "insert into EVENT (NAME) values (%(eventID)s)",
            dict(eventID=event.id)
        )


    async def storeIncident(self, incident: Incident) -> None:
        raise NotImplementedError("storeIncident()")


    async def storeIncidentReport(
        self, incidentReport: IncidentReport
    ) -> None:
        raise NotImplementedError("storeIncidentReport()")


    async def storeConcentricStreet(
        self, event: Event, streetID: str, streetName: str,
        ignoreDuplicates: bool = False,
    ) -> None:
        if ignoreDuplicates:
            ignore = " or ignore"
        else:
            ignore = ""

        await self._db.runOperation(
            f"""
            insert{ignore} into CONCENTRIC_STREET (EVENT, ID, NAME)
            values (
                (select ID from EVENT where NAME = %(eventID)s),
                %(streetID)s,
                %(streetName)s
            )
            """,
            dict(
                eventID=event.id, streetID=streetID, streetName=streetName
            )
        )


    async def storeIncidentType(self, name: str, hidden: bool) -> None:
        await self._db.runQuery(
            "insert into INCIDENT_TYPE (NAME, HIDDEN) "
            "values (%(name)s, %(hidden)s)",
            dict(name=name, hidden=hidden)
        )


    @staticmethod
    def normalizeIncidentAddress(incident: Incident) -> Incident:
        raise NotImplementedError("normalizeIncidentAddress()")
