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
Tests for L{ims.directory.clubhouse_db._dms}.
"""

from typing import cast

from ims.ext.trial import TestCase

from .._dms import DutyManagementSystem, fullName
from .dummy import DummyADBAPI, DummyConnectionPool, cannedPersonnel


__all__ = ()


class DutyManagementSystemTests(TestCase):
    """
    Tests for L{DutyManagementSystem}.
    """

    def setUp(self) -> None:
        """
        Patch adbapi module.
        """
        self.dummyADBAPI = DummyADBAPI()

        import ims.directory.clubhouse_db._dms

        self.patch(ims.directory.clubhouse_db._dms, "adbapi", self.dummyADBAPI)

    def dms(self) -> DutyManagementSystem:
        """
        Gimme a DMS.
        """
        self.host = "the-server"
        self.database = "the-db"
        self.username = "the-user"
        self.password = "the-password"  # nosec: B105

        return DutyManagementSystem(
            host=self.host,
            database=self.database,
            username=self.username,
            password=self.password,
            cacheInterval=5,
        )

    def test_init(self) -> None:
        """
        Initialized state is as expected.
        """
        dms = self.dms()

        self.assertEqual(dms.host, self.host)
        self.assertEqual(dms.database, self.database)
        self.assertEqual(dms.username, self.username)
        self.assertEqual(dms.password, self.password)

    def test_dbpool(self) -> None:
        """
        L{DutyManagementSystem.dbpool} returns a DB pool.
        """
        dms = self.dms()
        dbpool = cast(DummyConnectionPool, dms.dbpool)

        self.assertIsInstance(dbpool, DummyConnectionPool)

        self.assertEqual(dbpool.dbapiname, "pymysql")
        self.assertEqual(dbpool.connkw["host"], self.host)
        self.assertEqual(dbpool.connkw["database"], self.database)
        self.assertEqual(dbpool.connkw["user"], self.username)
        self.assertEqual(dbpool.connkw["password"], self.password)

    def test_personnel(self) -> None:
        """
        L{DutyManagementSystem.personnel} returns L{Ranger} objects.
        """
        dms = self.dms()

        personnel = self.successResultOf(dms.personnel())

        self.assertEqual(
            [p.handle for p in personnel],
            [p[1] for p in cannedPersonnel],
        )


class UtilTests(TestCase):
    """
    Tests for L{ims.directory.clubhouse_db}.
    """

    def test_fullName(self) -> None:
        """
        L{fullName} combines first/middle/last correctly.
        """
        self.assertEqual(fullName("Bob", "", "Smith"), "Bob Smith")
        self.assertEqual(fullName("Bob", "Q", "Smith"), "Bob Q. Smith")
