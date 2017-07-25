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

from hashlib import sha1
from os import urandom
from time import time
from typing import Iterable, Mapping, Optional, Sequence, Set, Tuple

from pymysql import (
    DatabaseError as SQLDatabaseError, OperationalError as SQLOperationalError
)

from twisted.enterprise import adbapi
from twisted.logger import Logger

from ims.model import Ranger, RangerStatus

Set, Sequence  # silence linter


__all__ = (
    "DMSError",
    "DatabaseError",
    "DutyManagementSystem",
)



class DMSError(Exception):
    """
    Duty Management System error.
    """



class DatabaseError(DMSError):
    """
    Database error.
    """



class Position(object):
    """
    A Ranger position.
    """

    def __init__(self, positionID: str, name: str) -> None:
        self.positionID = positionID
        self.name = name
        self.members: Set[Ranger] = set()



class DutyManagementSystem(object):
    """
    Duty Management System

    This class connects to an external system to get data.
    """

    _log = Logger()

    # DMS data changes rarely, so hour intervals between refreshing data should
    # be fine.
    # Refresh after an hour, but don't panic about it until we're stale for >12
    # hours.
    personnelCacheInterval    = 60 * 60 * 1   # 1 hour
    personnelCacheIntervalMax = 60 * 60 * 12  # 12 hours


    def __init__(
        self, host: Optional[str], database: Optional[str],
        username: Optional[str], password: Optional[str],
    ) -> None:
        """
        @param host: The name of the database host to connect to.

        @param database: The name of the database to access.

        @param username: The user name to use to access the database.

        @param password: The password to use to access the database.
        """
        self.host     = host
        self.database = database
        self.username = username
        self.password = password

        self._personnel: Sequence[Ranger] = ()
        self._personnelLastUpdated = 0.0
        self._dbpool: Optional[adbapi.ConnectionPool] = None
        self._busy = False


    @property
    def dbpool(self) -> adbapi.ConnectionPool:
        """
        Set up a database pool if needed and return it.
        """
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


    async def _queryPositionsByID(self) -> Mapping[str, Position]:
        self._log.info(
            "Retrieving positions from Duty Management System..."
        )

        rows = await self.dbpool.runQuery(
            """
            select id, title from position where all_rangers = 0
            """
        )

        return dict((id, Position(id, title)) for (id, title) in rows)


    async def _queryRangersByID(self) -> Mapping[str, Ranger]:
        self._log.info(
            "Retrieving personnel from Duty Management System..."
        )

        rows = await self.dbpool.runQuery(
            """
            select
                id,
                callsign, first_name, mi, last_name, email,
                status, on_site, password
            from person where status in ('active', 'inactive', 'vintage')
            """
        )

        return dict(
            (
                dmsID,
                Ranger(
                    handle=handle,
                    name=fullName(first, middle, last),
                    status=statusFromID(status),
                    email=(email,),
                    onSite=bool(onSite),
                    dmsID=int(dmsID),
                    password=password,
                )
            )
            for (
                dmsID, handle, first, middle, last, email,
                status, onSite, password,
            ) in rows
        )


    async def _queryPositionRangerJoin(self) -> Iterable[Tuple[str, str]]:
        self._log.info(
            "Retrieving position-personnel relations from "
            "Duty Management System..."
        )

        return await self.dbpool.runQuery(
            """
            select person_id, position_id from person_position
            """
        )


    async def positions(self) -> Iterable[Position]:
        """
        Look up all positions.
        """
        # Call self.personnel() to make sure we have current data, then return
        # self._positions, which will have been set.
        await self.personnel()
        return self._positions


    async def personnel(self) -> Iterable[Ranger]:
        """
        Look up all personnel.
        """
        now = time()
        elapsed = now - self._personnelLastUpdated

        if (not self._busy and elapsed > self.personnelCacheInterval):
            self._busy = True
            try:
                try:
                    rangersByID = await self._queryRangersByID()
                    positionsByID = await self._queryPositionsByID()
                    join = await self._queryPositionRangerJoin()

                    for rangerID, positionID in join:
                        position = positionsByID.get(positionID, None)
                        if position is None:
                            continue
                        ranger = rangersByID.get(rangerID, None)
                        if ranger is None:
                            continue
                        position.members.add(ranger)

                    self._personnel = tuple(rangersByID.values())
                    self._positions = tuple(positionsByID.values())
                    self._personnelLastUpdated = time()

                except Exception as e:
                    self._personnelLastUpdated = 0
                    self._dbpool = None

                    if isinstance(e, (SQLDatabaseError, SQLOperationalError)):
                        self._log.warn(
                            "Unable to load personnel data from DMS: {error}",
                            error=e
                        )
                    else:
                        self._log.failure(
                            "Unable to load personnel data from DMS"
                        )

                    if elapsed > self.personnelCacheIntervalMax:
                        raise DatabaseError(e)

            finally:
                self._busy = False

        try:
            return self._personnel
        except AttributeError:
            raise DMSError("No personnel data loaded.")



def fullName(first: str, middle: str, last: str) -> str:
    """
    Compose parts of a name into a full name.
    """
    if middle:
        format = "{first} {middle}. {last}"
    else:
        format = "{first} {last}"

    return format.format(first=first, middle=middle, last=last)


def statusFromID(strValue: str) -> RangerStatus:
    return {
        "active":      RangerStatus.active,
        "alpha":       RangerStatus.alpha,
        "bonked":      RangerStatus.bonked,
        "deceased":    RangerStatus.deceased,
        "inactive":    RangerStatus.inactive,
        "prospective": RangerStatus.prospective,
        "retired":     RangerStatus.retired,
        "uberbonked":  RangerStatus.uberbonked,
        "vintage":     RangerStatus.vintage,
    }.get(strValue, RangerStatus.other)


def hashPassword(password: str, salt: Optional[str] = None) -> str:
    """
    Compute a has for the given password
    """
    if salt is None:
        salt = urandom(16).decode("charmap")

    return salt + ":" + sha1(password.encode("utf-8")).hexdigest()


def verifyPassword(password: str, hashedPassword: str) -> bool:
    """
    Verify a password against a hashed password.
    """
    # Reference Clubhouse code: standard/controllers/security.php#L457

    # DMS password field is a salt and a SHA-1 hash (hex digest), separated by
    # ":".
    salt, hashValue = hashedPassword.split(":")

    hashed = sha1((salt + password).encode("utf-8")).hexdigest()

    return hashed == hashValue
