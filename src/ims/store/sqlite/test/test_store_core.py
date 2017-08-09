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
from typing import Dict, Optional, Set

from hypothesis import given
from hypothesis.strategies import integers

from ims.ext.sqlite import Connection, SQLiteError, createDB, printSchema

from .base import DataStoreTests
from .. import _store
from .._store import DataStore, asTimeStamp
from ..._exceptions import StorageError

Dict, Set  # silence linter


__all__ = ()



class DataStoreCoreTests(DataStoreTests):
    """
    Tests for :class:`DataStore` base functionality.
    """

    def test_loadSchema(self) -> None:
        """
        :meth:`DataStore.loadSchema` caches and returns the schema.
        """
        store = self.store()
        schema = store._loadSchema()

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


    def test_version(self) -> None:
        """
        :meth:`DataStore._version` returns the schema version for the given
        database.
        """
        for version in range(1, DataStore._schemaVersion + 1):
            db = createDB(None, DataStore._loadSchema(version=version))

            self.assertEqual(DataStore._version(db), version)


    def test_db(self) -> None:
        """
        :meth:`DataStore._db` returns a :class:`Connection`.
        """
        store = self.store()

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

        store = self.store()

        e = self.assertRaises(StorageError, lambda: store._db)
        self.assertEqual(
            str(e), f"Unable to open SQLite database {store.dbPath}: {message}"
        )


    def test_db_schemaUpgrade(self) -> None:
        """
        A database with an old schema is automatically upgraded to the current
        version.
        """
        def getSchemaInfo(db: Connection) -> str:
            out = StringIO()
            printSchema(db, out)
            return out.getvalue()

        currentVersion = DataStore._schemaVersion

        with createDB(
            None, DataStore._loadSchema(version=currentVersion)
        ) as db:
            currentSchemaInfo = getSchemaInfo(db)

        for version in range(1, currentVersion):
            path = Path(self.mktemp())
            createDB(path, DataStore._loadSchema(version=version))

            store = DataStore(dbPath=path)

            self.assertEqual(store._version(store._db), currentVersion)

            schemaInfo = getSchemaInfo(store._db)

            self.maxDiff = None
            self.assertEqual(schemaInfo, currentSchemaInfo)


    def test_db_noSchemaInfo(self) -> None:
        """
        :meth:`DataStore._db` raises :exc:`StorageError` when the database
        has no SCHEMA_INFO table.
        """
        # Load valid schema, then drop SCHEMA_INFO
        dbPath = Path(self.mktemp())
        with createDB(dbPath, DataStore._loadSchema()) as db:
            db.execute("drop table SCHEMA_INFO")

        store = self.store(dbPath=dbPath)

        e = self.assertRaises(StorageError, lambda: store._db)
        self.assertStartsWith(str(e), "Unable to look up schema version: ")
        self.assertIn("SCHEMA_INFO", str(e))


    def test_db_noSchemaVersion(self) -> None:
        """
        :meth:`DataStore._db` raises :exc:`StorageError` when the SCHEMA_INFO
        table has no rows.
        """
        # Load valid schema, then delete SCHEMA_INFO rows.
        dbPath = Path(self.mktemp())
        with createDB(dbPath, DataStore._loadSchema()) as db:
            db.execute("delete from SCHEMA_INFO")

        store = self.store(dbPath=dbPath)

        e = self.assertRaises(StorageError, lambda: store._db)
        self.assertEqual(str(e), "Invalid schema: no version")


    @given(integers(max_value=0))
    def test_db_fromVersionTooLow(self, version: int) -> None:
        """
        :meth:`DataStore._db` raises :exc:`StorageError` when the database
        has a schema version of zero or less.
        (Version numbering started at 1.)
        """
        # Load valid schema, then set schema version
        dbPath = Path(self.mktemp())
        with createDB(dbPath, DataStore._loadSchema()) as db:
            db.execute(
                "update SCHEMA_INFO set VERSION = :version",
                dict(version=version)
            )

        store = self.store(dbPath=dbPath)

        e = self.assertRaises(StorageError, lambda: store._db)
        self.assertEqual(
            str(e), f"No upgrade path from schema version {version}"
        )


    @given(integers(min_value=DataStore._schemaVersion + 1))
    def test_db_fromVersionTooHigh(self, version: int) -> None:
        """
        :meth:`DataStore._db` raises :exc:`StorageError` when the database
        has a schema version of greater than the current schema version.
        """
        # Load valid schema, then set schema version
        dbPath = Path(self.mktemp())
        with createDB(dbPath, DataStore._loadSchema()) as db:
            db.execute(
                "update SCHEMA_INFO set VERSION = :version",
                dict(version=version)
            )

        store = self.store(dbPath=dbPath)

        e = self.assertRaises(StorageError, lambda: store._db)
        self.assertEqual(
            str(e), f"Schema version {version} is too new"
        )



class DataStoreHelperTests(DataStoreTests):
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
