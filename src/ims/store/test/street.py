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
Street tests for :mod:`ranger-ims-server.store`
"""

from ims.ext.trial import asyncAsDeferred
from ims.model import Event

from .base import DataStoreTests


__all__ = ()


class DataStoreConcentricStreetTests(DataStoreTests):
    """
    Tests for :class:`IMSDataStore` concentric street access.
    """

    @asyncAsDeferred
    async def test_concentricStreets(self) -> None:
        """
        :meth:`IMSDataStore.createConcentricStreet` returns the concentric
        streets for the given event.
        """
        for event, streetID, streetName in (
            (Event(id="Foo"), "A", "Alpha"),
            (Event(id="Foo Bar"), "B", "Bravo"),
            (Event(id="XYZZY"), "C", "Charlie"),
        ):
            store = await self.store()

            await store.createEvent(event)
            await store.storeConcentricStreet(event.id, streetID, streetName)

            concentricStreets = await store.concentricStreets(event.id)

            self.assertEqual(len(concentricStreets), 1)
            self.assertEqual(concentricStreets.get(streetID), streetName)

    @asyncAsDeferred
    async def test_createConcentricStreet(self) -> None:
        """
        :meth:`IMSDataStore.createConcentricStreet` creates a concentric
        streets for the given event.
        """
        for event, streetID, streetName in (
            (Event(id="Foo"), "A", "Alpha"),
            (Event(id="Foo Bar"), "B", "Bravo"),
            (Event(id="XYZZY"), "C", "Charlie"),
        ):
            store = await self.store()

            await store.createEvent(event)
            await store.createConcentricStreet(
                eventID=event.id, id=streetID, name=streetName
            )

            stored = await store.concentricStreets(eventID=event.id)

            self.assertEqual(len(stored), 1)
            self.assertEqual(stored.get(streetID), streetName)
