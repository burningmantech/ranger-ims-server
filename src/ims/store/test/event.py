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

from abc import ABC, abstractmethod
from typing import Iterable

from hypothesis import given
from hypothesis.strategies import frozensets, text

from ims.model import Event
from ims.model.strategies import events

from .._abc import IMSDataStore
from .._exceptions import StorageError


__all__ = ()



class DataStoreEventTests(ABC):
    """
    Tests for :class:`DataStore` event access.
    """

    @abstractmethod
    def store(self) -> IMSDataStore:
        """
        Return a data store for use in tests.
        """


    def test_events(self, broken: bool = False) -> None:
        """
        :meth:`DataStore.events` returns all events.
        """
        store = self.store()

        for event in (Event(id="Event A"), Event(id="Event B")):
            store.storeEvent(event)

        if broken:
            store.bringThePain()

        events = frozenset(self.successResultOf(store.events()))

        self.assertEqual(events, {Event(id="Event A"), Event(id="Event B")})


    def test_events_error(self) -> None:
        """
        :meth:`DataStore.events` raises `StorageError` if SQLite raises.
        """
        e = self.assertRaises(StorageError, self.test_events, broken=True)
        self.assertEqual(str(e), self.store().exceptionMessage)


    @given(events())
    def test_createEvent(self, event: Event) -> None:
        """
        :meth:`DataStore.createEvent` creates the given event.
        """
        store = self.store()
        self.successResultOf(store.createEvent(event))
        stored = frozenset(self.successResultOf(store.events()))
        self.assertEqual(stored, frozenset((event,)))


    def test_createEvent_error(self) -> None:
        """
        :meth:`DataStore.createEvent` raises `StorageError` if SQLite raises.
        """
        store = self.store()
        store.bringThePain()

        f = self.failureResultOf(store.createEvent(Event(id="x")))
        f.printTraceback()
        self.assertEqual(f.type, StorageError)


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


    @given(events(), frozensets(text()))
    def test_setReaders(self, event: Event, readers: Iterable[str]) -> None:
        """
        :meth:`DataStore.setReaders` sets the read ACL for an event.
        """
        store = self.store()
        self.successResultOf(store.createEvent(event))
        self.successResultOf(store.setReaders(event, readers))
        result = frozenset(self.successResultOf(store.readers(event)))
        self.assertEqual(result, readers)


    def test_setReaders_error(self) -> None:
        """
        :meth:`DataStore.setReaders` raises :exc:`StorageError` when SQLite
        raises an exception.
        """
        event = Event(id="foo")
        store = self.store()
        self.successResultOf(store.createEvent(event))
        store.bringThePain()
        f = self.failureResultOf(store.setReaders(event, ()))
        self.assertEqual(f.type, StorageError)


    @given(events(), frozensets(text()))
    def test_setWriters(self, event: Event, writers: Iterable[str]) -> None:
        """
        :meth:`DataStore.setWriters` sets the write ACL for an event.
        """
        store = self.store()
        self.successResultOf(store.createEvent(event))
        self.successResultOf(store.setWriters(event, writers))
        result = frozenset(self.successResultOf(store.writers(event)))
        self.assertEqual(result, writers)


    def test_setWriters_error(self) -> None:
        """
        :meth:`DataStore.setWriters` raises :exc:`StorageError` when SQLite
        raises an exception.
        """
        event = Event(id="foo")
        store = self.store()
        self.successResultOf(store.createEvent(event))
        store.bringThePain()
        f = self.failureResultOf(store.setWriters(event, ()))
        self.assertEqual(f.type, StorageError)
