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

from typing import ClassVar, cast

from attr import attrib, attrs

from ims.ext.sqlite import Connection, SQLITE_MAX_INT, SQLiteError

from .._store import DataStore
from ...test.database import TestDatabaseStoreMixIn


__all__ = ()


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class TestDataStore(DataStore, TestDatabaseStoreMixIn):
    """
    See :class:`SuperTestDataStore`.
    """

    firstSchemaVersion: ClassVar[int] = 1
    maxIncidentNumber: ClassVar[int] = SQLITE_MAX_INT
    exceptionClass: ClassVar[type] = SQLiteError

    @attrs(frozen=False, auto_attribs=True, kw_only=True, eq=False)
    class _State(DataStore._State):
        """
        Internal mutable state for :class:`DataStore`.
        """

        broken: bool = False

    _state: _State = attrib(factory=_State, init=False)

    @property
    def _db(self) -> Connection:
        if getattr(self._state, "broken", False):
            self.raiseException()

        return cast(
            Connection,
            DataStore._db.fget(self),  # type: ignore[attr-defined]
        )

    def bringThePain(self) -> None:
        self._state.broken = True
