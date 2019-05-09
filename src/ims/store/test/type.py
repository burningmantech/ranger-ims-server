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
Incident type tests for :mod:`ranger-ims-server.store`
"""

from typing import Tuple, cast

from .base import DataStoreTests, asyncAsDeferred
from .._exceptions import StorageError


__all__ = ()


builtInTypes = {"Admin", "Junk"}



class DataStoreIncidentTypeTests(DataStoreTests):
    """
    Tests for :class:`IMSDataStore` incident type access.
    """

    @asyncAsDeferred
    async def test_incidentTypes(self) -> None:
        """
        :meth:`IMSDataStore.incidentTypes` returns visible incident types.
        """
        for _data in (
            (),
            (
                ("MOOP", False),
            ),
            (
                ("MOOP", True),
            ),
            (
                ("MOOP", False),
                ("Law Enforcement", False),
                ("Old Type", True),
                ("Foo", True),
            ),
        ):
            data = cast(Tuple[Tuple[str, bool]], _data)

            store = await self.store()
            for name, hidden in data:
                await store.storeIncidentType(name, hidden)

            incidentTypes = frozenset(await store.incidentTypes())
            expected = frozenset(
                (name for (name, hidden) in data if not hidden)
            ) | builtInTypes

            self.assertEqual(incidentTypes, expected)


    @asyncAsDeferred
    async def test_incidentTypes_includeHidden(self) -> None:
        """
        :meth:`IMSDataStore.incidentTypes` if given CL{includeHidden=True}
        returns all incident types.
        """
        for _data in (
            (),
            (
                ("MOOP", False),
            ),
            (
                ("MOOP", True),
            ),
            (
                ("MOOP", False),
                ("Law Enforcement", False),
                ("Old Type", True),
                ("Foo", True),
            ),
        ):
            data = cast(Tuple[Tuple[str, bool]], _data)

            store = await self.store()
            for name, hidden in data:
                await store.storeIncidentType(name, hidden)

            incidentTypes = frozenset(
                await store.incidentTypes(includeHidden=True)
            )
            expected = (
                frozenset((name for (name, hidden) in data)) | builtInTypes
            )

            self.assertEqual(incidentTypes, expected)


    @asyncAsDeferred
    async def test_createIncidentType(self) -> None:
        """
        :meth:`IMSDataStore.createIncidentType` creates the incident type.
        """
        for incidentType, hidden in (
            ("MOOP", False),
            ("Law Enforcement", False),
            ("Old Type", True),
            ("Foo", True),
        ):
            store = await self.store()
            await store.createIncidentType(incidentType, hidden=hidden)

            incidentTypes = frozenset(await store.incidentTypes())
            if hidden:
                self.assertNotIn(incidentType, incidentTypes)
            else:
                self.assertIn(incidentType, incidentTypes)

            incidentTypes = frozenset(
                await store.incidentTypes(includeHidden=True)
            )
            self.assertIn(incidentType, incidentTypes)


    @asyncAsDeferred
    async def test_createIncidentType_duplicate(self) -> None:
        """
        :meth:`IMSDataStore.createIncidentType` raises :exc:`StorageError` when
        given an incident type that already exists in the data store.
        """
        incidentType = "foo"
        store = await self.store()

        await store.createIncidentType(incidentType)

        try:
            await store.createIncidentType(incidentType)
        except StorageError:
            pass
        else:
            self.fail("StorageError not raised")


    @asyncAsDeferred
    async def test_showIncidentTypes(self) -> None:
        """
        :meth:`IMSDataStore.showIncidentTypes` makes the given incident types
        visible.
        """
        incidentType = "foo"
        store = await self.store()

        await store.createIncidentType(incidentType, hidden=True)
        self.assertNotIn(incidentType, await store.incidentTypes())

        await store.showIncidentTypes((incidentType,))
        self.assertIn(incidentType, await store.incidentTypes())

        # Again should also work
        await store.showIncidentTypes((incidentType,))
        self.assertIn(incidentType, await store.incidentTypes())


    @asyncAsDeferred
    async def test_hideIncidentTypes(self) -> None:
        """
        :meth:`IMSDataStore.showIncidentTypes` makes the given incident types
        hidden.
        """
        incidentType = "foo"
        store = await self.store()

        await store.createIncidentType(incidentType, hidden=False)
        self.assertIn(incidentType, await store.incidentTypes())

        await store.hideIncidentTypes((incidentType,))
        self.assertNotIn(incidentType, await store.incidentTypes())

        # Again should also work
        await store.hideIncidentTypes((incidentType,))
        self.assertNotIn(incidentType, await store.incidentTypes())
