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
from typing import Tuple

from hypothesis import assume, given
from hypothesis.strategies import booleans, text, tuples

from ims.ext.sqlite import Connection
from ims.ext.trial import TestCase
from ims.model import Event, Incident, Ranger
from ims.model.json.test.strategies import events, incidents, rangers

from .._store import DataStore
from ..._exceptions import StorageError


__all__ = ()



class DataStoreTests(TestCase):
    """
    Tests for :class:`DataStore`
    """

    builtInTypes = {"Admin", "Junk"}


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
                insert into EVENT (NAME) values ('Event A');
                insert into EVENT (NAME) values ('Event B');
                """
            )
        )

        events = frozenset(self.successResultOf(store.events()))

        self.assertEqual(events, {Event("Event A"), Event("Event B")})


    @given(events())
    def test_createEvent(self, event: Event) -> None:
        """
        :meth:`DataStore.createEvent` creates the given event.
        """
        store = self.store()
        self.successResultOf(store.createEvent(event))
        stored = frozenset(self.successResultOf(store.events()))
        self.assertEqual(stored, frozenset((event,)))


    def test_createEvent_duplicate(self) -> None:
        """
        :meth:`DataStore.createEvent` raises :exc:`StorageError` when given an
        event that already exists in the data store.
        """
        event = Event(id="foo")
        store = self.store()
        self.successResultOf(store.createEvent(event))
        f = self.failureResultOf(store.createEvent(event))
        self.assertEqual(f.type, StorageError)


    @given(tuples(tuples(text(), booleans())))
    def test_incidentTypes(self, data: Tuple[Tuple[str, bool]]) -> None:
        """
        :meth:`DataStore.incidentTypes` returns visible incident types.
        """
        store = self.store()
        for (name, hidden) in data:
            assume(name not in self.builtInTypes)
            store._db.execute(
                "insert into INCIDENT_TYPE (NAME, HIDDEN) "
                "values (:name, :hidden)",
                dict(name=name, hidden=hidden)
            )

        incidentTypes = frozenset(
            self.successResultOf(store.incidentTypes())
        )
        expected = frozenset(
            (name for (name, hidden) in data if not hidden)
        ) | self.builtInTypes

        self.assertEqual(incidentTypes, expected)


    @given(tuples(tuples(text(), booleans())))
    def test_incidentTypes_includeHidden(
        self, data: Tuple[Tuple[str, bool]]
    ) -> None:
        """
        :meth:`DataStore.incidentTypes` if given CL{includeHidden=True} returns
        all incident types.
        """
        store = self.store()
        for (name, hidden) in data:
            assume(name not in self.builtInTypes)
            store._db.execute(
                "insert into INCIDENT_TYPE (NAME, HIDDEN) "
                "values (:name, :hidden)",
                dict(name=name, hidden=hidden)
            )

        incidentTypes = frozenset(
            self.successResultOf(store.incidentTypes(includeHidden=True))
        )
        expected = frozenset(
            (name for (name, hidden) in data)
        ) | self.builtInTypes

        self.assertEqual(incidentTypes, expected)


    @given(text(), booleans())
    def test_createIncidentType(self, incidentType: str, hidden: bool) -> None:
        """
        :meth:`DataStore.createIncidentType` creates the incident type.
        """
        assume(incidentType not in self.builtInTypes)

        store = self.store()
        self.successResultOf(
            store.createIncidentType(incidentType, hidden=hidden)
        )

        incidentTypes = frozenset(self.successResultOf(store.incidentTypes()))
        if hidden:
            self.assertNotIn(incidentType, incidentTypes)
        else:
            self.assertIn(incidentType, incidentTypes)

        incidentTypes = frozenset(
            self.successResultOf(store.incidentTypes(includeHidden=True))
        )
        self.assertIn(incidentType, incidentTypes)


    def test_createIncidentType_duplicate(self) -> None:
        """
        :meth:`DataStore.createIncidentType` raises :exc:`StorageError` when
        given an incident type that already exists in the data store.
        """
        incidentType = "foo"
        store = self.store()
        self.successResultOf(store.createIncidentType(incidentType))
        f = self.failureResultOf(store.createIncidentType(incidentType))
        self.assertEqual(f.type, StorageError)


    def test_showIncidentTypes(self) -> None:
        """
        :meth:`DataStore.showIncidentTypes` makes the given incident types
        visible.
        """
        incidentType = "foo"
        store = self.store()
        self.successResultOf(
            store.createIncidentType(incidentType, hidden=True)
        )
        self.assertNotIn(
            incidentType, self.successResultOf(store.incidentTypes())
        )
        self.successResultOf(store.showIncidentTypes((incidentType,)))
        self.assertIn(
            incidentType, self.successResultOf(store.incidentTypes())
        )
        # Again should also work
        self.successResultOf(store.showIncidentTypes((incidentType,)))
        self.assertIn(
            incidentType, self.successResultOf(store.incidentTypes())
        )


    def test_hideIncidentTypes(self) -> None:
        """
        :meth:`DataStore.showIncidentTypes` makes the given incident types
        hidden.
        """
        incidentType = "foo"
        store = self.store()
        self.successResultOf(
            store.createIncidentType(incidentType, hidden=False)
        )
        self.assertIn(
            incidentType, self.successResultOf(store.incidentTypes())
        )
        self.successResultOf(store.hideIncidentTypes((incidentType,)))
        self.assertNotIn(
            incidentType, self.successResultOf(store.incidentTypes())
        )
        # Again should also work
        self.successResultOf(store.hideIncidentTypes((incidentType,)))
        self.assertNotIn(
            incidentType, self.successResultOf(store.incidentTypes())
        )


    def test_incidents(self) -> None:
        """
        :meth:`DataStore.incidents` returns all incidents.
        """
        raise NotImplementedError()

    test_incidents.todo = "unimplemented test"


    @given(events(), incidents(), rangers())
    def test_createIncident(
        self, event: Event, incident: Incident, author: Ranger
    ) -> None:
        """
        :meth:`DataStore.createIncident` creates the given incident.
        """
        store = self.store()

        store.createEvent(event)

        self.successResultOf(
            store.createIncident(event=event, incident=incident, author=author)
        )
        stored = frozenset(self.successResultOf(store.incidents(event=event)))
        self.assertEqual(stored, frozenset((incident,)))

    test_createIncident.todo = "unimplemented"
