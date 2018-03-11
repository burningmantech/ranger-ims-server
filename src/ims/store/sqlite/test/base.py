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

from datetime import datetime as DateTime, timedelta as TimeDelta
from pathlib import Path
from typing import Optional, cast

from ims.ext.sqlite import Connection, SQLITE_MAX_INT, SQLiteError
from ims.ext.trial import TestCase

from .._store import DataStore
from ...test.database import TestDatabaseStoreMixIn


__all__ = ()



class TestDataStore(DataStore, TestDatabaseStoreMixIn):
    """
    See :class:`SuperTestDataStore`.
    """

    maxIncidentNumber = SQLITE_MAX_INT

    exceptionClass = SQLiteError


    def __init__(
        self, testCase: TestCase, dbPath: Optional[Path] = None
    ) -> None:
        if dbPath is None:
            dbPath = Path(testCase.mktemp())
        DataStore.__init__(self, dbPath)


    @property
    def _db(self) -> Connection:
        if getattr(self._state, "broken", False):
            self.raiseException()

        return cast(property, DataStore._db).fget(self)


    def bringThePain(self) -> None:
        setattr(self._state, "broken", True)
        assert getattr(self._state, "broken")


    def dateTimesEqual(self, a: DateTime, b: DateTime) -> bool:
        # Floats stored in SQLite may be slightly off when round-tripped.
        return a - b < TimeDelta(microseconds=20)
