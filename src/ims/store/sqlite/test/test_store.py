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

from io import StringIO
from pathlib import Path
from textwrap import dedent

from .._store import DataStore
from ....ext.sqlite import Connection
from ....ext.trial import TestCase
from ....model import Event


__all__ = ()



class DataStoreTests(TestCase):
    """
    Tests for :class:`DataStore`
    """

    def store(self) -> DataStore:
        return DataStore(dbPath=Path(self.mktemp()))


    def test_loadSchema(self) -> None:
        """
        :meth:`DataStore.loadSchema` caches and returns the schema.
        """
        store = self.store()

        DataStore._schema = None  # Reset in case previously cached
        schema = store._loadSchema()
        self.assertIsInstance(schema, str)

        # Check that class and instance access are the same object
        self.assertIdentical(schema, store._schema)
        self.assertIdentical(schema, DataStore._schema)


    def test_printSchema(self) -> None:
        """
        :meth:`DataStore.printSchema` prints the expected schema.
        """
        out = StringIO()
        DataStore.printSchema(out)
        schemaInfo = out.getvalue()
        self.assertEqual(
            schemaInfo,
            dedent(
                """
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
                  3: CREATED(integer) not null
                  4: PRIORITY(integer) not null
                  5: STATE(text) not null
                  6: SUMMARY(text)
                  7: LOCATION_NAME(text)
                  8: LOCATION_CONCENTRIC(integer)
                  9: LOCATION_RADIAL_HOUR(integer)
                  10: LOCATION_RADIAL_MINUTE(integer)
                  11: LOCATION_DESCRIPTION(text)
                INCIDENT_INCIDENT_REPORT:
                  0: EVENT(integer) not null *1
                  1: INCIDENT_NUMBER(integer) not null *2
                  2: INCIDENT_REPORT_NUMBER(integer) not null *3
                INCIDENT_REPORT:
                  0: NUMBER(integer) not null *1
                  1: CREATED(integer) not null
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
                  3: CREATED(integer) not null
                  4: GENERATED(numeric) not null
                SCHEMA_INFO:
                  0: VERSION(integer) not null
                """[1:]
            )
        )


    def test_db(self) -> None:
        """
        :meth:`DataStore._db` returns a :class:`Connection`.
        """
        store = self.store()
        self.assertIsInstance(store._db, Connection)


    def test_events(self) -> None:
        """
        :meth:`DataStore.events` returns all events.
        """
        store = self.store()
        store._db.executescript(
            dedent(
                """
                insert or ignore into EVENT (NAME) values ('Event A');
                insert or ignore into EVENT (NAME) values ('Event B');
                """
            )
        )

        events = frozenset(self.successResultOf(store.events()))

        self.assertEqual(events, {Event("Event A"), Event("Event B")})
