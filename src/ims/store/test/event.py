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
Event tests for :mod:`ranger-ims-server.store`
"""

from ims.ext.trial import asyncAsDeferred
from ims.model import Event

from .._exceptions import StorageError
from .base import DataStoreTests


__all__ = ()


class DataStoreEventTests(DataStoreTests):
    """
    Tests for :class:`IMSDataStore` event access.
    """

    @asyncAsDeferred
    async def test_events(self, broken: bool = False) -> None:
        """
        :meth:`IMSDataStore.events` returns all events.
        """
        store = await self.store()

        for event in (Event(id="Event A"), Event(id="Event B")):
            await store.storeEvent(event)

        if broken:
            store.bringThePain()

        events = frozenset(await store.events())

        self.assertEqual(events, {Event(id="Event A"), Event(id="Event B")})

    @asyncAsDeferred
    async def test_events_error(self) -> None:
        """
        :meth:`IMSDataStore.events` raises `StorageError` if the store raises.
        """
        try:
            await self.test_events(broken=True)
        except StorageError as e:
            store = await self.store()
            self.assertEqual(str(e), store.exceptionMessage)
        else:
            self.fail("StorageError not raised")

    @asyncAsDeferred
    async def test_createEvent(self) -> None:
        """
        :meth:`IMSDataStore.createEvent` creates the given event.
        """
        for eventName in ("Foo", "Foo Bar"):
            event = Event(id=eventName)

            store = await self.store()
            await store.createEvent(event)
            stored = frozenset(await store.events())
            self.assertEqual(stored, frozenset((event,)))

    @asyncAsDeferred
    async def test_createEvent_error(self) -> None:
        """
        :meth:`IMSDataStore.createEvent` raises `StorageError` if the store
        raises.
        """
        store = await self.store()
        store.bringThePain()

        try:
            await store.createEvent(Event(id="x"))
        except StorageError:
            pass
        else:
            self.fail("StorageError not raised")

    @asyncAsDeferred
    async def test_createEvent_duplicate(self) -> None:
        """
        :meth:`IMSDataStore.createEvent` raises :exc:`StorageError` when given
        an event that already exists in the data store.
        """
        event = Event(id="foo")
        store = await self.store()
        await store.createEvent(event)

        try:
            await store.createEvent(event)
        except StorageError:
            pass
        else:
            self.fail("StorageError not raised")

    @asyncAsDeferred
    async def test_setReaders(self) -> None:
        """
        :meth:`IMSDataStore.setReaders` sets the read ACL for an event.
        """
        event = Event(id="Foo")

        for readers in ({"a"}, {"a", "b", "c"}):
            store = await self.store()
            await store.createEvent(event)
            await store.setReaders(event, readers)
            result = frozenset(await store.readers(event))
            self.assertEqual(result, readers)

    @asyncAsDeferred
    async def test_setReaders_error(self) -> None:
        """
        :meth:`IMSDataStore.setReaders` raises :exc:`StorageError` when the
        store raises an exception.
        """
        event = Event(id="foo")
        store = await self.store()
        await store.createEvent(event)
        store.bringThePain()

        try:
            await store.setReaders(event, ())
        except StorageError:
            pass
        else:
            self.fail("StorageError not raised")

    @asyncAsDeferred
    async def test_setWriters(self) -> None:
        """
        :meth:`IMSDataStore.setWriters` sets the write ACL for an event.
        """
        event = Event(id="Foo")

        for writers in ({"a"}, {"a", "b", "c"}):
            store = await self.store()
            await store.createEvent(event)
            await store.setWriters(event, writers)
            result = frozenset(await store.writers(event))
            self.assertEqual(result, writers)

    @asyncAsDeferred
    async def test_setWriters_error(self) -> None:
        """
        :meth:`IMSDataStore.setWriters` raises :exc:`StorageError` when the
        store raises an exception.
        """
        event = Event(id="foo")
        store = await self.store()
        await store.createEvent(event)
        store.bringThePain()

        try:
            await store.setWriters(event, ())
        except StorageError:
            pass
        else:
            self.fail("StorageError not raised")
