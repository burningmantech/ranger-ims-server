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

from os import environ
from typing import List, Optional, cast

from twisted.internet.defer import ensureDeferred
from twisted.logger import Logger

from .base import TestDataStore
from .service import MySQLService
from ...test.base import (
    DataStoreTests as SuperDataStoreTests, TestDataStoreABC
)
from ...test.event import DataStoreEventTests as SuperDataStoreEventTests
from ...test.incident import (
    DataStoreIncidentTests as SuperDataStoreIncidentTests
)
from ...test.report import (
    DataStoreIncidentReportTests as SuperDataStoreIncidentReportTests
)
from ...test.street import (
    DataStoreConcentricStreetTests as SuperDataStoreConcentricStreetTests
)
from ...test.type import (
    DataStoreIncidentTypeTests as SuperDataStoreIncidentTypeTests
)


__all__ = ()



if environ.get("IMS_TEST_MYSQL_HOST", None) is None:
    from .service import DockerizedMySQLService

    def mysqlServiceFactory() -> MySQLService:
        return DockerizedMySQLService()
else:
    from .service import ExternalMySQLService

    def mysqlServiceFactory() -> MySQLService:
        env = environ.get
        return ExternalMySQLService(
            host=env("IMS_TEST_MYSQL_HOST"),
            port=int(env("IMS_TEST_MYSQL_PORT", "3306")),
            user=env("IMS_TEST_MYSQL_USERNAME", "ims"),
            password=env("IMS_TEST_MYSQL_PASSWORD", "ims"),
            rootPassword=env("IMS_TEST_MYSQL_PASSWORD", "ims"),
        )


class DataStoreTests(SuperDataStoreTests):
    """
    Parent test class.
    """

    log = Logger()

    skip: Optional[str] = None

    mysqlService: MySQLService = mysqlServiceFactory()


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


    async def store(self) -> TestDataStoreABC:
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

        return cast(TestDataStoreABC, store)



class DataStoreEventTests(DataStoreTests, SuperDataStoreEventTests):
    """
    Tests for :class:`DataStore` event access.
    """



class DataStoreIncidentTests(DataStoreTests, SuperDataStoreIncidentTests):
    """
    Tests for :class:`DataStore` incident access.
    """



class DataStoreIncidentReportTests(
    DataStoreTests, SuperDataStoreIncidentReportTests
):
    """
    Tests for :class:`DataStore` incident report access.
    """



class DataStoreConcentricStreetTests(
    DataStoreTests, SuperDataStoreConcentricStreetTests
):
    """
    Tests for :class:`DataStore` concentric street access.
    """



class DataStoreIncidentTypeTests(
    DataStoreTests, SuperDataStoreIncidentTypeTests
):
    """
    Tests for :class:`DataStore` incident type access.
    """
