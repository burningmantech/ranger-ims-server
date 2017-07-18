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

from typing import Dict, Set

from hypothesis import given

from ims.model import Event
from ims.model.strategies import (
    concentricStreetIDs, concentricStreetNames, events
)

from .base import DataStoreTests

Dict, Set  # silence linter


__all__ = ()



class DataStoreConcentricStreetTests(DataStoreTests):
    """
    Tests for :class:`DataStore` concentric street access.
    """

    @given(events(), concentricStreetIDs(), concentricStreetNames())
    def test_concentricStreets(
        self, event: Event, streetID: str, streetName: str
    ) -> None:
        """
        :meth:`DataStore.createConcentricStreet` returns the concentric streets
        for the given event.
        """
        store = self.store()

        self.successResultOf(store.createEvent(event))

        self.storeConcentricStreet(store._db, event, streetID, streetName)

        concentricStreets = self.successResultOf(
            store.concentricStreets(event)
        )

        self.assertEqual(len(concentricStreets), 1)
        self.assertEqual(concentricStreets.get(streetID), streetName)


    @given(events(), concentricStreetIDs(), concentricStreetNames())
    def test_createConcentricStreet(
        self, event: Event, id: str, name: str
    ) -> None:
        """
        :meth:`DataStore.createConcentricStreet` creates a concentric streets
        for the given event.
        """
        store = self.store()

        self.successResultOf(store.createEvent(event))

        self.successResultOf(
            store.createConcentricStreet(event=event, id=id, name=name)
        )
        stored = self.successResultOf(store.concentricStreets(event=event))

        self.assertEqual(len(stored), 1)
        self.assertEqual(stored.get(id), name)
