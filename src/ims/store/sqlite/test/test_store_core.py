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
Tests for :mod:`ranger-ims-server.store.sqlite._store`
"""

from datetime import (
    datetime as DateTime, timedelta as TimeDelta, timezone as TimeZone
)
from io import StringIO
from pathlib import Path
from textwrap import dedent
from typing import Optional

from hypothesis import given
from hypothesis.strategies import integers

from ims.ext.sqlite import Connection, SQLiteError, createDB, printSchema
from ims.ext.trial import AsynchronousTestCase, TestCase

from .base import TestDataStore
from .. import _store
from .._store import DataStore, asTimeStamp
from ..._exceptions import StorageError


__all__ = ()



class DataStoreCoreTests(AsynchronousTestCase):
    """
    Tests for :class:`DataStore` base functionality.
    """

    def test_loadSchema(self) -> None:
        """
        :meth:`DataStore.loadSchema` caches and returns the schema.
        """
        store = TestDataStore(self)
        schema = store.loadSchema()

        self.assertStartsWith(schema, "create table SCHEMA_INFO (")


    def test_printSchema(self) -> None:
        """
        :meth:`DataStore.printSchema` prints the expected schema.
        """
        out = StringIO()
        DataStore.printSchema(out)
        schemaInfo = out.getvalue()

        self.maxDiff = None
        self.assertEqual(
            schemaInfo,
            dedent(
                """
                Version: 2
                ACCESS_MODE:
                  0: ID(text) not null *1
                CONCENTRIC_STREET:
                  0: EVENT(integer) not null *1
                  1: ID(text) not null *2
                  2: NAME(text) not null
                EVENT:
                  0: ID(integer) not null *1
                  1: NAME(text) not null
                EVENT_ACCESS:
                  0: EVENT(integer) not null *1
                  1: EXPRESSION(text) not null *2
                  2: MODE(text) not null
                INCIDENT:
                  0: EVENT(integer) not null *1
                  1: NUMBER(integer) not null *2
                  2: VERSION(integer) not null
                  3: CREATED(real) not null
                  4: PRIORITY(integer) not null
                  5: STATE(text) not null
                  6: SUMMARY(text)
                  7: LOCATION_NAME(text)
                  8: LOCATION_CONCENTRIC(text)
                  9: LOCATION_RADIAL_HOUR(integer)
                  10: LOCATION_RADIAL_MINUTE(integer)
                  11: LOCATION_DESCRIPTION(text)
                INCIDENT_REPORT:
                  0: NUMBER(integer) not null *1
                  1: CREATED(real) not null
                  2: SUMMARY(text)
                INCIDENT_REPORT__REPORT_ENTRY:
                  0: INCIDENT_REPORT_NUMBER(integer) not null *1
                  1: REPORT_ENTRY(integer) not null *2
                INCIDENT_STATE:
                  0: ID(text) not null *1
                INCIDENT_TYPE:
                  0: ID(integer) not null *1
                  1: NAME(text) not null
                  2: HIDDEN(numeric) not null
                INCIDENT__INCIDENT_REPORT:
                  0: EVENT(integer) not null *1
                  1: INCIDENT_NUMBER(integer) not null *2
                  2: INCIDENT_REPORT_NUMBER(integer) not null *3
                INCIDENT__INCIDENT_TYPE:
                  0: EVENT(integer) not null *1
                  1: INCIDENT_NUMBER(integer) not null *2
                  2: INCIDENT_TYPE(integer) not null *3
                INCIDENT__RANGER:
                  0: EVENT(integer) not null *1
                  1: INCIDENT_NUMBER(integer) not null *2
                  2: RANGER_HANDLE(text) not null *3
                INCIDENT__REPORT_ENTRY:
                  0: EVENT(integer) not null *1
                  1: INCIDENT_NUMBER(integer) not null *2
                  2: REPORT_ENTRY(integer) not null *3
                REPORT_ENTRY:
                  0: ID(integer) not null *1
                  1: AUTHOR(text) not null
                  2: TEXT(text) not null
                  3: CREATED(real) not null
                  4: GENERATED(numeric) not null
                SCHEMA_INFO:
                  0: VERSION(integer) not null
                """[1:]
            )
        )


    def test_printQueries(self) -> None:
        """
        :meth:`DataStore.printQueries` prints the queries in use.
        """
        out = StringIO()
        DataStore.printQueries(out)
        queryInfo = out.getvalue()

        self.assertStartsWith(
            queryInfo,
            "addEventAccess:\n\n"
            "  -- query --\n\n"
            "    insert into EVENT_ACCESS (EVENT, EXPRESSION, MODE)\n"
            "    values ((select ID from EVENT where NAME = :eventID), "
            ":expression, :mode)\n\n"
            "  -- query plan --\n\n"
            "    [None,None] You did not supply a value for binding 1.\n\n"
            "addReportEntry:\n\n"
            "  -- query --\n\n"
            "    insert into REPORT_ENTRY (AUTHOR, TEXT, CREATED, GENERATED)\n"
            "    values (:author, :text, :created, :generated)\n\n"
            "  -- query plan --\n\n"
            "    [None,None] You did not supply a value for binding 1.\n\n"
        )


    def test_dbSchemaVersion(self) -> None:
        """
        :meth:`DataStore._dbSchemaVersion` returns the schema version for the
        given database.
        """
        for version in range(1, DataStore.schemaVersion + 1):
            db = createDB(None, DataStore.loadSchema(version=version))

            self.assertEqual(DataStore._dbSchemaVersion(db), version)


    def test_db(self) -> None:
        """
        :meth:`DataStore._db` returns a :class:`Connection`.
        """
        store = TestDataStore(self)

        self.assertIsInstance(store._db, Connection)


    def test_db_error(self) -> None:
        """
        :meth:`DataStore._db` raises :exc:`StorageError` when SQLite raises
        an exception.
        """
        message = "Nyargh"

        def oops(path: Path, schema: Optional[str] = None) -> Connection:
            raise SQLiteError(message)

        self.patch(_store, "openDB", oops)

        store = TestDataStore(self)

        e = self.assertRaises(StorageError, lambda: store._db)
        self.assertEqual(
            str(e), f"Unable to open SQLite database {store.dbPath}: {message}"
        )


    def test_upgradeSchema(self) -> None:
        """
        :meth:`DataStore.upgradeSchema` upgrades the data schema to the current
        version.
        """
        def getSchemaInfo(db: Connection) -> str:
            out = StringIO()
            printSchema(db, out)
            return out.getvalue()

        currentVersion = DataStore.schemaVersion

        with createDB(
            None, DataStore.loadSchema(version=currentVersion)
        ) as db:
            currentSchemaInfo = getSchemaInfo(db)

        for version in range(1, currentVersion):
            path = Path(self.mktemp())
            createDB(path, DataStore.loadSchema(version=version))

            store = DataStore(dbPath=path)
            self.successResultOf(store.upgradeSchema())

            self.assertEqual(store._dbSchemaVersion(store._db), currentVersion)

            schemaInfo = getSchemaInfo(store._db)

            self.maxDiff = None
            self.assertEqual(schemaInfo, currentSchemaInfo)


    def test_upgradeSchema_noSchemaInfo(self) -> None:
        """
        :meth:`DataStore.upgradeSchema` raises :exc:`StorageError` when the
        database has no SCHEMA_INFO table.
        """
        # Load valid schema, then drop SCHEMA_INFO
        dbPath = Path(self.mktemp())
        with createDB(dbPath, DataStore.loadSchema()) as db:
            db.execute("drop table SCHEMA_INFO")

        store = TestDataStore(self, dbPath=dbPath)

        self.failureResultOf(store.upgradeSchema(), StorageError)


    def test_upgradeSchema_noSchemaVersion(self) -> None:
        """
        :meth:`DataStore.upgradeSchema` raises :exc:`StorageError` when the
        SCHEMA_INFO table has no rows.
        """
        # Load valid schema, then delete SCHEMA_INFO rows.
        dbPath = Path(self.mktemp())
        with createDB(dbPath, DataStore.loadSchema()) as db:
            db.execute("delete from SCHEMA_INFO")

        store = TestDataStore(self, dbPath=dbPath)

        f = self.failureResultOf(store.upgradeSchema(), StorageError)
        self.assertEqual(f.getErrorMessage(), "Invalid schema: no version")


    @given(integers(max_value=-1))
    def test_upgradeSchema_fromVersionTooLow(self, version: int) -> None:
        """
        :meth:`DataStore.upgradeSchema` raises :exc:`StorageError` when the
        database has a schema version less than 0.
        """
        # Load valid schema, then set schema version
        dbPath = Path(self.mktemp())
        with createDB(dbPath, DataStore.loadSchema()) as db:
            db.execute(
                "update SCHEMA_INFO set VERSION = :version",
                dict(version=version)
            )

        store = TestDataStore(self, dbPath=dbPath)

        f = self.failureResultOf(store.upgradeSchema(), StorageError)
        self.assertEqual(
            f.getErrorMessage(),
            f"No upgrade path from schema version {version}",
        )


    @given(integers(min_value=DataStore.schemaVersion + 1))
    def test_upgradeSchema_fromVersionTooHigh(self, version: int) -> None:
        """
        :meth:`DataStore.upgradeSchema` raises :exc:`StorageError` when the
        database has a schema version of greater than the current schema
        version.
        """
        # Load valid schema, then set schema version
        dbPath = Path(self.mktemp())
        with createDB(dbPath, DataStore.loadSchema()) as db:
            db.execute(
                "update SCHEMA_INFO set VERSION = :version",
                dict(version=version)
            )

        store = TestDataStore(self, dbPath=dbPath)

        f = self.failureResultOf(store.upgradeSchema(), StorageError)
        self.assertEqual(
            f.getErrorMessage(),
            f"Schema version {version} is too new "
            f"(current version is {store.schemaVersion})"
        )



class DataStoreHelperTests(TestCase):
    """
    Tests for :class:`DataStore` helper functions.
    """

    def test_asTimeStamp_preEpoch(self) -> None:
        """
        :func:`asTimeStamp` raises :exc:`StorageError` when given a time stamp
        before the UTC Epoch.
        """
        epoch = DateTime(
            year=1970, month=1, day=1, hour=0, minute=0, tzinfo=TimeZone.utc
        )
        preEpoch = epoch - TimeDelta(seconds=1)

        e = self.assertRaises(StorageError, asTimeStamp, preEpoch)
        self.assertStartsWith(str(e), "DateTime is before the UTC epoch: ")
