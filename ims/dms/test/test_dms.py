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
Tests for L{ims.dms}.
"""

from twisted.trial import unittest

from twisted.internet.defer import succeed, fail
from twisted.internet.defer import inlineCallbacks

from .. import DutyManagementSystem
from .._dms import fullName



class DutyManagementSystemTests(unittest.TestCase):
    """
    Tests for L{ims.dms.DutyManagementSystem}.
    """

    def setUp(self):
        """
        Patch adbapi module.
        """
        self.dummyADBAPI = DummyADBAPI()

        import ims.dms._dms
        self.patch(ims.dms._dms, "adbapi", self.dummyADBAPI)


    def dms(self):
        """
        Gimme a DMS.
        """
        self.host = u"the-server"
        self.database = u"the-db"
        self.username = u"the-user"
        self.password = u"the-password"

        return DutyManagementSystem(
            host=self.host,
            database=self.database,
            username=self.username,
            password=self.password,
        )


    def test_init(self):
        """
        Initialized state is as expected.
        """
        dms = self.dms()

        self.assertEquals(dms.host, self.host)
        self.assertEquals(dms.database, self.database)
        self.assertEquals(dms.username, self.username)
        self.assertEquals(dms.password, self.password)


    def test_dbpool(self):
        """
        L{DutyManagementSystem.dbpool} returns a DB pool.
        """
        dms = self.dms()
        dbpool = dms.dbpool

        self.assertIsInstance(dbpool, DummyConnectionPool)

        self.assertEquals(dbpool.dbapiname, "mysql.connector")
        self.assertEquals(dbpool.connkw["host"], self.host)
        self.assertEquals(dbpool.connkw["database"], self.database)
        self.assertEquals(dbpool.connkw["user"], self.username)
        self.assertEquals(dbpool.connkw["password"], self.password)


    @inlineCallbacks
    def test_personnel(self):
        """
        L{DutyManagementSystem.personnel} returns L{Ranger} objects.
        """
        dms = self.dms()

        personnel = yield dms.personnel()

        self.assertEquals(
            [p.handle for p in personnel],
            [p[0] for p in cannedPersonnel],
        )



class UtilTests(unittest.TestCase):
    """
    Tests for L{ims.dms}.
    """

    def test_fullName(self):
        """
        L{fullName} combines first/middle/last correctly.
        """
        self.assertEquals(fullName("Bob", "", "Smith"), "Bob Smith")
        self.assertEquals(fullName("Bob", "Q", "Smith"), "Bob Q. Smith")



class DummyQuery(object):
    """
    Represents a call to C{runQuery}.
    """

    def __init__(self, args, kwargs):
        self.args = args
        self.kwargs = kwargs


    def sql(self):
        """
        Produce normalized SQL for the query.
        """
        sql = self.args[0]

        # Collapse spaces
        sql = " ".join(sql.split())

        return sql



class DummyConnectionPool(object):
    """
    Mock for L{adbapi.ConnectionPool}.
    """

    def __init__(self, dbapiname, **connkw):
        self.dbapiname = dbapiname
        self.connkw = connkw
        self.queries = []


    def runQuery(self, *args, **kw):
        query = DummyQuery(args, kw)

        self.queries.append(query)

        sql = query.sql()

        if sql == (
            "select callsign, first_name, mi, last_name, status "
            "from person "
            "where status not in "
            "( 'prospective', 'alpha', 'bonked', 'uberbonked', 'deceased' )"
        ):
            return succeed(iter(cannedPersonnel))

        return fail(
            AssertionError("No canned response for query: {0}".format(sql))
        )



class DummyADBAPI(object):
    """
    Mock for L{adbapi}.
    """

    def __init__(self):
        self.ConnectionPool = DummyConnectionPool



cannedPersonnel = (
    ("Easy E", "Eric", "P", "Grant", "active"),
    ("El Weso", "Wes", "", "Johnson", "active"),
    ("SciFi", "Fred", "", "McCord", "active"),
    ("Slumber", "Sleepy", "T", "Dwarf", "inactive"),
    ("Tool", "Wilfredo", "", "Sanchez", "vintage"),
    ("Tulsa", "Curtis", "", "Kline", "vintage"),
)
