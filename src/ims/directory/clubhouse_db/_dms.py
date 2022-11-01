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

from collections.abc import Iterable, Mapping
from time import time
from typing import ClassVar, cast

from attr import Factory, attrib, attrs
from pymysql import DatabaseError as SQLDatabaseError
from pymysql import OperationalError as SQLOperationalError
from twisted.enterprise import adbapi
from twisted.internet.defer import CancelledError
from twisted.logger import Logger

from ims.model import Ranger, RangerStatus

from .._directory import DirectoryError


__all__ = ()


@attrs(frozen=False, auto_attribs=True, auto_exc=True)
class DMSError(DirectoryError):
    """
    Duty Management System error.
    """

    message: str


@attrs(frozen=False, auto_attribs=True, auto_exc=True)
class DatabaseError(DMSError):
    """
    Database error.
    """


@attrs(frozen=False, auto_attribs=True, kw_only=True)
class Position:
    """
    A Ranger position.
    """

    positionID: str
    name: str
    members: set[Ranger] = Factory(set)


@attrs(frozen=True, auto_attribs=True, kw_only=True, eq=False)
class DutyManagementSystem:
    """
    Duty Management System

    This class connects to an external system to get data.
    """

    _log: ClassVar[Logger] = Logger()

    @attrs(frozen=False, auto_attribs=True, kw_only=True, eq=False)
    class _State:
        """
        Internal mutable state for :class:`Configuration`.
        """

        _personnel: Iterable[Ranger] = attrib(default=(), init=False)
        _positions: Iterable[Position] = attrib(default=(), init=False)
        _personnelLastUpdated: float = attrib(default=0.0, init=False)
        _dbpool: adbapi.ConnectionPool | None = attrib(default=None, init=False)
        _busy: bool = attrib(default=False, init=False)
        _dbErrorCount: int = attrib(default=0, init=False)

    host: str
    database: str
    username: str
    password: str = attrib(repr=lambda _: "*")
    cacheInterval: int

    _state: _State = attrib(factory=_State, init=False, repr=False)

    @property
    def dbpool(self) -> adbapi.ConnectionPool:
        """
        Set up a database pool if needed and return it.
        """
        if self._state._dbpool is None:
            if (
                not self.host
                and not self.database
                and not self.username
                and not self.password
            ):
                from .test.test_dms import DummyConnectionPool

                dbpool = cast(
                    adbapi.ConnectionPool, DummyConnectionPool("Dummy")
                )

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

            self._state._dbpool = dbpool

        return self._state._dbpool

    async def _queryPositionsByID(self) -> Mapping[str, Position]:
        self._log.info("Retrieving positions from Duty Management System...")

        rows = await self.dbpool.runQuery(
            """
            select id, title from position where all_rangers = 0
            """
        )

        return {id: Position(positionID=id, name=title) for (id, title) in rows}

    async def _queryRangersByID(self) -> Mapping[str, Ranger]:
        self._log.info("Retrieving personnel from Duty Management System...")

        rows = await self.dbpool.runQuery(
            """
            select
                id,
                callsign, first_name, mi, last_name, email,
                status, on_site, password
            from person
            where status in ('active', 'inactive', 'vintage', 'auditor')
            """
        )

        return {
            directoryID: Ranger(
                handle=handle,
                name=fullName(first, middle, last),
                status=statusFromID(status),
                email=(email,),
                enabled=bool(enabled),
                directoryID=directoryID,
                password=password,
            )
            for (
                directoryID,
                handle,
                first,
                middle,
                last,
                email,
                status,
                enabled,
                password,
            ) in rows
        }

    async def _queryPositionRangerJoin(self) -> Iterable[tuple[str, str]]:
        self._log.info(
            "Retrieving position-personnel relations from "
            "Duty Management System..."
        )

        return cast(
            Iterable[tuple[str, str]],
            await self.dbpool.runQuery(
                """
                select person_id, position_id from person_position
                """
            ),
        )

    async def positions(self) -> Iterable[Position]:
        """
        Look up all positions.
        """
        # Call self.personnel() to make sure we have current data, then return
        # self._state._positions, which will have been set.
        await self.personnel()
        return self._state._positions

    async def personnel(self) -> Iterable[Ranger]:
        """
        Look up all personnel.
        """
        now = time()
        elapsed = now - self._state._personnelLastUpdated

        if not self._state._busy and elapsed > self.cacheInterval:
            self._state._busy = True
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

                    self._state._personnel = tuple(rangersByID.values())
                    self._state._positions = tuple(positionsByID.values())
                    self._state._personnelLastUpdated = time()
                    self._state._dbErrorCount = 0

                except Exception as e:
                    self._state._personnelLastUpdated = 0
                    self._state._dbpool = None
                    self._state._dbErrorCount += 1

                    if isinstance(e, (SQLDatabaseError, SQLOperationalError)):
                        if self._state._dbErrorCount < 2:
                            self._log.info(
                                "Retrying loading personnel from DMS "
                                "after error: {error}",
                                error=e,
                            )
                            return await self.personnel()
                        self._log.critical(
                            "Failed to load personnel data from DMS "
                            "after error: {error}",
                            error=e,
                        )
                    elif isinstance(e, CancelledError):
                        pass
                    else:
                        self._log.failure(
                            "Unable to load personnel data from DMS"
                        )

                    if elapsed > self.cacheInterval * 5:
                        raise DatabaseError(
                            f"Unable to load expired personnel data "
                            f"from DMS: {e}"
                        ) from e

            finally:
                self._state._busy = False

        try:
            return self._state._personnel
        except AttributeError:
            raise DMSError("No personnel data loaded.") from None


def fullName(first: str, middle: str, last: str) -> str:
    """
    Compose parts of a name into a full name.
    """
    if middle:
        return f"{first} {middle}. {last}"
    else:
        return f"{first} {last}"


def statusFromID(strValue: str) -> RangerStatus:
    return {
        "active": RangerStatus.active,
        "inactive": RangerStatus.inactive,
        "vintage": RangerStatus.vintage,
    }.get(strValue, RangerStatus.other)
