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
from typing import List, cast

from twisted.internet.defer import ensureDeferred

from ims.ext.trial import AsynchronousTestCase

from .base import TestDataStore
from .service import MySQLService
from ...test.base import asyncAsDeferred


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
            host=cast(str, env("IMS_TEST_MYSQL_HOST")),
            port=int(env("IMS_TEST_MYSQL_PORT", "3306")),
            user=env("IMS_TEST_MYSQL_USERNAME", "ims"),
            password=env("IMS_TEST_MYSQL_PASSWORD", ""),
            rootPassword=env("IMS_TEST_MYSQL_ROOT_PASSWORD", ""),
        )



class DataStoreCoreTests(AsynchronousTestCase):
    """
    Tests for :class:`DataStore` base functionality.
    """

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


    async def store(self) -> TestDataStore:
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

        self.stores.append(store)

        return store


    @asyncAsDeferred
    async def test_loadSchema(self) -> None:
        """
        :meth:`DataStore.loadSchema` caches and returns the schema.
        """
        store = await self.store()
        schema = store.loadSchema()

        self.assertStartsWith(schema, "create table SCHEMA_INFO (")
