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
Duty Management System.
"""

__all__ = [
    "DMSError",
    "DatabaseError",
    "DutyManagementSystem",
]

from time import time

from twisted.logger import Logger
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.enterprise import adbapi

from ..data import Ranger



class DMSError(Exception):
    """
    Duty Management System error.
    """



class DatabaseError(DMSError):
    """
    Database error.
    """



class DutyManagementSystem(object):
    """
    Duty Management System

    This class connects to an external system to get data.
    """
    log = Logger()

    # DMS data changes rarely, so hour intervals between refreshing data should
    # be fine.
    # Refresh after an hour, but don't panic about it until we're stale for >12
    # hours.
    personnelCacheInterval    = 60 * 60 * 1   # 1 hour
    personnelCacheIntervalMax = 60 * 60 * 12  # 12 hours


    def __init__(self, host, database, username, password):
        """
        @param host: The name of the database host to connect to.
        @type host: L{unicode}

        @param database: The name of the database to access.
        @type database: L{unicode}

        @param username: The user name to use to access the database.
        @type username: L{unicode}

        @param password: The password to use to access the database.
        @type password: L{unicode}
        """
        self.host     = host
        self.database = database
        self.username = username
        self.password = password

        self._personnel = ()
        self._personnelLastUpdated = 0
        self._dbpool = None
        self._busy = False


    @property
    def dbpool(self):
        if self._dbpool is None:
            if (
                self.host is None and
                self.database is None and
                self.username is None and
                self.password is None
            ):
                from .test.test_dms import DummyConnectionPool
                dbpool = DummyConnectionPool("Dummy")

            else:
                dbpool = adbapi.ConnectionPool(
                    "mysql.connector",
                    host=self.host,
                    database=self.database,
                    user=self.username,
                    password=self.password,
                )

            if dbpool is None:
                raise DatabaseError("Unable to set up database pool.")

            self._dbpool = dbpool

        return self._dbpool


    @inlineCallbacks
    def personnel(self):
        now = time()
        elapsed = now - self._personnelLastUpdated

        if (not self._busy and elapsed > self.personnelCacheInterval):
            self._busy = True
            try:
                try:
                    self.log.info(
                        "Retrieving personnel from Duty Management System..."
                    )

                    results = yield self.dbpool.runQuery(
                        """
                        select
                            callsign, first_name, mi, last_name,
                            status, password
                        from person
                        where status not in (
                            'prospective', 'alpha',
                            'bonked', 'uberbonked',
                            'deceased'
                        )
                        """
                    )

                    self._personnel = tuple(
                        Ranger(
                            handle,
                            fullName(first, middle, last),
                            status,
                            password=password
                        )
                        for handle, first, middle, last, status, password
                        in results
                    )
                    self._personnelLastUpdated = time()

                except Exception as e:
                    self._personnelLastUpdated = 0
                    self._dbpool = None

                    if elapsed > self.personnelCacheIntervalMax:
                        raise DatabaseError(e)

                    self.log.warn(
                        "Unable to load personnel data from DMS: {error}",
                        error=e
                    )

            finally:
                self._busy = False

        returnValue(self._personnel)



def fullName(first, middle, last):
    values = dict(first=first, middle=middle, last=last)
    if middle:
        return u"{first} {middle}. {last}".format(**values)
    else:
        return u"{first} {last}".format(**values)
