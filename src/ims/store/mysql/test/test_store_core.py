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

from io import StringIO
from os import environ
from textwrap import dedent
from typing import ClassVar, cast
from unittest.mock import patch

from twisted.internet.defer import Deferred, ensureDeferred
from twisted.logger import Logger

from ims.ext.trial import AsynchronousTestCase, asyncAsDeferred

from ..._exceptions import StorageError
from .._store import DataStore, ReconnectingConnectionPool
from .base import TestDataStore
from .service import DatabaseExistsError, MySQLService, randomDatabaseName


__all__ = ()


if environ.get("IMS_TEST_MYSQL_HOST", None) is None:
    from .service import DockerizedMySQLService

    def mysqlServiceFactory() -> MySQLService:
        Logger().info("Using test MySQL service via Docker")
        return DockerizedMySQLService()


else:
    from .service import ExternalMySQLService

    def mysqlServiceFactory() -> MySQLService:
        Logger().info("Using configured test MySQL service")
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

    _log: ClassVar[Logger] = Logger()

    mysqlService: ClassVar[MySQLService] = mysqlServiceFactory()

    def setUp(self) -> Deferred[None]:  # type: ignore[override]
        async def setUp() -> None:
            self.stores: list[TestDataStore] = []

            await self.mysqlService.start()

        # setUp can't return a coroutine, so convert it to a Deferred
        return ensureDeferred(setUp())

    def tearDown(self) -> Deferred[None]:  # type: ignore[override]
        async def tearDown() -> None:
            for store in self.stores:
                await store.disconnect()

            await self.mysqlService.stop()

        # setUp can't return a coroutine, so convert it to a Deferred
        return ensureDeferred(tearDown())

    async def store(self) -> TestDataStore:
        service = self.mysqlService

        assert service.host is not None
        assert service.port is not None

        for _ in range(100):
            databaseName = randomDatabaseName()
            try:
                self._log.info("Creating database: {name}", name=databaseName)
                await service.createDatabase(name=databaseName)
            except DatabaseExistsError:
                self._log.warn(
                    "Database {name} already exists.", name=databaseName
                )
            else:
                break
        else:
            raise AssertionError("Unable to generate unique database name")

        store = TestDataStore(
            hostName=service.host,
            hostPort=service.port,
            database=databaseName,
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

    @asyncAsDeferred
    async def test_printSchema(self) -> None:
        """
        :meth:`DataStore.printSchema` prints the expected schema.
        """
        store = await self.store()
        await store.upgradeSchema()

        out = StringIO()
        await store.printSchema(out)
        schemaInfo = out.getvalue()

        self.maxDiff = None
        self.assertEqual(
            dedent(
                """
                Version: 6
                CONCENTRIC_STREET:
                  1: EVENT(int) not null
                  2: ID(varchar(16)) not null
                  3: NAME(varchar(128)) not null
                EVENT:
                  1: ID(int) not null
                  2: NAME(varchar(128)) not null
                EVENT_ACCESS:
                  1: EVENT(int) not null
                  2: EXPRESSION(varchar(128)) not null
                  3: MODE(enum(6)) not null
                INCIDENT:
                  1: EVENT(int) not null
                  2: NUMBER(int) not null
                  3: CREATED(double) not null
                  4: PRIORITY(tinyint) not null
                  5: STATE(enum(10)) not null
                  6: SUMMARY(varchar(1024))
                  7: LOCATION_NAME(varchar(1024))
                  8: LOCATION_CONCENTRIC(varchar(64))
                  9: LOCATION_RADIAL_HOUR(tinyint)
                  10: LOCATION_RADIAL_MINUTE(tinyint)
                  11: LOCATION_DESCRIPTION(varchar(1024))
                INCIDENT_REPORT:
                  1: EVENT(int) not null
                  2: NUMBER(int) not null
                  3: CREATED(double) not null
                  4: SUMMARY(varchar(1024))
                  5: INCIDENT_NUMBER(int)
                INCIDENT_REPORT__REPORT_ENTRY:
                  1: EVENT(int) not null
                  2: INCIDENT_REPORT_NUMBER(int) not null
                  3: REPORT_ENTRY(int) not null
                INCIDENT_TYPE:
                  1: ID(int) not null
                  2: NAME(varchar(128)) not null
                  3: HIDDEN(tinyint) not null
                INCIDENT__INCIDENT_TYPE:
                  1: EVENT(int) not null
                  2: INCIDENT_NUMBER(int) not null
                  3: INCIDENT_TYPE(int) not null
                INCIDENT__RANGER:
                  1: EVENT(int) not null
                  2: INCIDENT_NUMBER(int) not null
                  3: RANGER_HANDLE(varchar(64)) not null
                INCIDENT__REPORT_ENTRY:
                  1: EVENT(int) not null
                  2: INCIDENT_NUMBER(int) not null
                  3: REPORT_ENTRY(int) not null
                REPORT_ENTRY:
                  1: ID(int) not null
                  2: AUTHOR(varchar(64)) not null
                  3: TEXT(text(65535)) not null
                  4: CREATED(double) not null
                  5: GENERATED(tinyint) not null
                  6: STRICKEN(tinyint) not null
                SCHEMA_INFO:
                  1: VERSION(smallint) not null
                """[
                    1:
                ]
            ),
            schemaInfo,
        )

    @asyncAsDeferred
    async def test_dbSchemaVersion(self) -> None:
        """
        :meth:`DataStore._dbSchemaVersion` returns the schema version for the
        given database.
        """
        for version in range(
            TestDataStore.firstSchemaVersion, DataStore.schemaVersion + 1
        ):
            with patch("ims.store.mysql.DataStore.schemaVersion", version):
                store = await self.store()

                # Confirm we're starting with a blank database
                currentVersion = await store.dbSchemaVersion()
                assert currentVersion == 0

                # Upgrade and confirm we're at the desired version
                await store.upgradeSchema()
                currentVersion = await store.dbSchemaVersion()
                self.assertEqual(currentVersion, version)

    @asyncAsDeferred
    async def test_db(self) -> None:
        """
        :meth:`DataStore._db` returns a :class:`ReconnectingConnectionPool`.
        """
        store = await self.store()

        self.assertIsInstance(store._db, ReconnectingConnectionPool)

    @asyncAsDeferred
    async def test_upgradeSchema(self) -> None:
        """
        :meth:`DataStore.upgradeSchema` upgrades the data schema to the current
        version.
        """

        async def getSchemaInfo(store: DataStore) -> str:
            out = StringIO()
            await store.printSchema(out)
            return out.getvalue()

        latestVersion = DataStore.schemaVersion

        store = await self.store()
        await store.upgradeSchema()
        latestSchemaInfo = await getSchemaInfo(store)

        for fromVersion in range(
            TestDataStore.firstSchemaVersion, latestVersion
        ):
            store = await self.store()

            # Confirm we're starting with a blank database
            currentVersion = await store.dbSchemaVersion()
            assert currentVersion == 0

            # Upgrade to starting version and confirm we're there
            await store.upgradeSchema(fromVersion)
            currentVersion = await store.dbSchemaVersion()
            assert currentVersion == fromVersion, currentVersion

            # Upgrade to latest version and confirm we're there
            await store.upgradeSchema()
            currentVersion = await store.dbSchemaVersion()
            self.assertEqual(currentVersion, latestVersion)

            # Make sure the schema is as we expect
            currentSchemaInfo = await getSchemaInfo(store)
            self.maxDiff = None
            self.assertEqual(currentSchemaInfo, latestSchemaInfo)

    @asyncAsDeferred
    async def test_upgradeSchema_noSchemaInfo(self) -> None:
        """
        :meth:`DataStore.upgradeSchema` raises :exc:`StorageError` when the
        database has no SCHEMA_INFO table.
        """
        store = await self.store()
        await store.upgradeSchema()

        # Nuke the SCHEMA_INFO table
        await store._db.runOperation("drop table SCHEMA_INFO")

        try:
            await store.upgradeSchema()
        except StorageError as e:
            self.assertStartsWith(str(e), "Unable to upgrade schema from ")
        else:
            self.fail("StorageError not raised.")

    @asyncAsDeferred
    async def test_upgradeSchema_noSchemaVersion(self) -> None:
        """
        :meth:`DataStore.upgradeSchema` raises :exc:`StorageError` when the
        SCHEMA_INFO table has no rows.
        """
        store = await self.store()
        await store.upgradeSchema()

        # Nuke the SCHEMA_INFO table's contents
        await store._db.runOperation("delete from SCHEMA_INFO")

        try:
            await store.upgradeSchema()
        except StorageError as e:
            self.assertStartsWith(str(e), "Invalid schema: no version")
        else:
            self.fail("StorageError not raised.")

    @asyncAsDeferred
    async def test_upgradeSchema_fromVersionTooLow(self) -> None:
        """
        :meth:`DataStore.upgradeSchema` raises :exc:`StorageError` when the
        database has a schema version less than 0.
        """
        # FIXME: Use hypothesis, except async
        version = -1

        store = await self.store()
        await store.upgradeSchema()

        # Override schema version
        await store._db.runOperation(
            "update SCHEMA_INFO set VERSION = %(version)s",
            dict(version=version),
        )

        try:
            await store.upgradeSchema()
        except StorageError as e:
            self.assertEqual(
                str(e), f"No upgrade path from schema version {version}"
            )
        else:
            self.fail("StorageError not raised.")

    @asyncAsDeferred
    async def test_upgradeSchema_fromVersionTooHigh(self) -> None:
        """
        :meth:`DataStore.upgradeSchema` raises :exc:`StorageError` when the
        database has a schema version of greater than the current schema
        version.
        """
        # FIXME: Use hypothesis, except async
        version = DataStore.schemaVersion + 1

        store = await self.store()
        await store.upgradeSchema()

        # Override schema version
        await store._db.runOperation(
            "update SCHEMA_INFO set VERSION = %(version)s",
            dict(version=version),
        )

        try:
            await store.upgradeSchema()
        except StorageError as e:
            self.assertEqual(
                str(e),
                f"Schema version {version} is too new "
                f"(latest version is {store.schemaVersion})",
            )
        else:
            self.fail("StorageError not raised.")
