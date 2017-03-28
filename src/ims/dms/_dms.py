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

from pymysql import (
    DatabaseError as SQLDatabaseError, OperationalError as SQLOperationalError
)

from twisted.logger import Logger
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.enterprise import adbapi

from ..data.model import Ranger



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
                    "pymysql",
                    host=self.host,
                    database=self.database,
                    user=self.username,
                    password=self.password,
                )

            if dbpool is None:
                raise DatabaseError("Unable to set up database pool.")

            self._dbpool = dbpool

        return self._dbpool


    def _queryPositions(self):
        self.log.info(
            "Retrieving positions from Duty Management System..."
        )

        d = self.dbpool.runQuery(
            """
            select id, title from position where all_rangers = 0
            """
        )

        def gotRows(rows):
            return dict(
                (id, Position(id, title.decode("utf-8")))
                for (id, title) in rows
            )

        d.addCallback(gotRows)
        return d


    def _queryRangers(self):
        self.log.info(
            "Retrieving personnel from Duty Management System..."
        )

        d = self.dbpool.runQuery(
            """
            select
                id,
                callsign, first_name, mi, last_name, email,
                status, on_site, password
            from person where status in ('active', 'inactive', 'vintage')
            """
        )

        def string(bytesString):
            if bytesString is None:
                return None
            return bytesString.decode("utf-8")

        def gotRows(rows):
            return dict(
                (
                    dmsID,
                    Ranger(
                        string(handle),
                        fullName(
                            string(first),
                            string(middle),
                            string(last),
                        ),
                        string(status),
                        dmsID=int(dmsID),
                        email=string(email),
                        onSite=bool(onSite),
                        password=string(password),
                    )
                )
                for (
                    dmsID, handle, first, middle, last, email,
                    status, onSite, password,
                ) in rows
            )

        d.addCallback(gotRows)
        return d


    def _queryPositionRangerJoin(self):
        self.log.info(
            "Retrieving position-personnel relations from "
            "Duty Management System..."
        )

        d = self.dbpool.runQuery(
            """
            select person_id, position_id from person_position
            """
        )
        return d


    def positions(self):
        # Call self.personnel() to make sure we have current data, then return
        # self._positions, which will have been set.
        d = self.personnel()
        d.addCallback(lambda _: self._positions)
        return d


    @inlineCallbacks
    def personnel(self):
        now = time()
        elapsed = now - self._personnelLastUpdated

        if (not self._busy and elapsed > self.personnelCacheInterval):
            self._busy = True
            try:
                try:
                    rangersByID = yield self._queryRangers()
                    positionsByID = yield self._queryPositions()
                    join = yield self._queryPositionRangerJoin()

                    for rangerID, positionID in join:
                        position = positionsByID.get(positionID, None)
                        if position is None:
                            continue
                        ranger = rangersByID.get(rangerID, None)
                        if ranger is None:
                            continue
                        position.members.add(ranger)

                    self._personnel = tuple(rangersByID.itervalues())
                    self._positions = tuple(positionsByID.itervalues())
                    self._personnelLastUpdated = time()

                except Exception as e:
                    self._personnelLastUpdated = 0
                    self._dbpool = None

                    if isinstance(e, (SQLDatabaseError, SQLOperationalError)):
                        self.log.warn(
                            "Unable to load personnel data from DMS: {error}",
                            error=e
                        )
                    else:
                        self.log.failure(
                            "Unable to load personnel data from DMS"
                        )

                    if elapsed > self.personnelCacheIntervalMax:
                        raise DatabaseError(e)

            finally:
                self._busy = False

        try:
            returnValue(self._personnel)
        except AttributeError:
            raise DMSError("No personnel data loaded.")



class Position(object):
    def __init__(self, positionID, name):
        self.positionID = positionID
        self.name = name
        self.members = set()



def fullName(first, middle, last):
    if middle:
        format = "{first} {middle}. {last}"
    else:
        format = "{first} {last}"

    return format.format(first=first, middle=middle, last=last)
