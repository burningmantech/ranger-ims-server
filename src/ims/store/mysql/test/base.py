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
Tests for :mod:`ranger-ims-server.store.mysql._store`
"""

from typing import cast

from pymysql.err import MySQLError

from twisted.enterprise.adbapi import ConnectionPool

from ims.ext.trial import TestCase

from .._store import DataStore
from ...test.database import TestDatabaseStoreMixIn


__all__ = ()



class TestDataStore(DataStore, TestDatabaseStoreMixIn):
    """
    See :class:`SuperTestDataStore`.
    """

    maxIncidentNumber = 4294967295

    exceptionClass = MySQLError


    def __init__(
        self, testCase: TestCase,
        hostName: str,
        hostPort: int,
        database: str,
        username: str,
        password: str,
    ) -> None:
        DataStore.__init__(
            self,
            hostName=hostName, hostPort=hostPort,
            database=database,
            username=username, password=password,
        )
        setattr(self._state, "testCase", testCase)


    @property
    def _db(self) -> ConnectionPool:
        if getattr(self._state, "broken", False):
            self.raiseException()

        return cast(property, DataStore._db).fget(self)


    def bringThePain(self) -> None:
        setattr(self._state, "broken", True)
        assert getattr(self._state, "broken")
