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

from typing import Dict, Set, Tuple

from hypothesis import given
from hypothesis.strategies import booleans, tuples

from ims.model.strategies import incidentTypesText

from .base import DataStoreTests
from ..._exceptions import StorageError

Dict, Set  # silence linter


__all__ = ()


builtInTypes = {"Admin", "Junk"}



class DataStoreIncidentTypeTests(DataStoreTests):
    """
    Tests for :class:`DataStore` incident type access.
    """

    @given(
        tuples(
            tuples(incidentTypesText(), booleans()).filter(
                lambda t: t[0] not in builtInTypes
            )
        )
    )
    def test_incidentTypes(self, data: Tuple[Tuple[str, bool]]) -> None:
        """
        :meth:`DataStore.incidentTypes` returns visible incident types.
        """
        store = self.store()
        for (name, hidden) in data:
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
        ) | builtInTypes

        self.assertEqual(incidentTypes, expected)


    @given(
        tuples(
            tuples(incidentTypesText(), booleans()).filter(
                lambda t: t[0] not in builtInTypes
            )
        )
    )
    def test_incidentTypes_includeHidden(
        self, data: Tuple[Tuple[str, bool]]
    ) -> None:
        """
        :meth:`DataStore.incidentTypes` if given CL{includeHidden=True} returns
        all incident types.
        """
        store = self.store()
        for (name, hidden) in data:
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
        ) | builtInTypes

        self.assertEqual(incidentTypes, expected)


    @given(
        incidentTypesText().filter(lambda t: t not in builtInTypes),
        booleans(),
    )
    def test_createIncidentType(self, incidentType: str, hidden: bool) -> None:
        """
        :meth:`DataStore.createIncidentType` creates the incident type.
        """
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
