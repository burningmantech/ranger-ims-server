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

from attrs import field, frozen, mutable
from pymysql import DatabaseError as SQLDatabaseError
from pymysql import OperationalError as SQLOperationalError
from twisted.enterprise import adbapi
from twisted.internet.defer import CancelledError
from twisted.logger import Logger

from ims.model import Ranger, RangerStatus

from .._directory import DirectoryError


__all__ = ()


@mutable
class DMSError(DirectoryError):
    """
    Duty Management System error.
    """

    message: str


@mutable
class DatabaseError(DMSError):
    """
    Database error.
    """


@frozen
class Position:
    """
    A Ranger position.
    """

    positionID: str
    name: str
    members: set[Ranger] = field(factory=set)


@frozen
class Team:
    """
    A Ranger team.
    """

    teamID: str
    name: str
    members: set[Ranger] = field(factory=set)


@frozen(kw_only=True, eq=False)
class DutyManagementSystem:
    """
    Duty Management System

    This class connects to an external system to get data.
    """

    _log: ClassVar[Logger] = Logger()

    @mutable(kw_only=True, eq=False)
    class _State:
        """
        Internal mutable state for :class:`Configuration`.
        """

        _personnel: Iterable[Ranger] = field(default=(), init=False)
        _positions: Iterable[Position] = field(default=(), init=False)
        _teams: Iterable[Team] = field(default=(), init=False)
        _personnelLastUpdated: float = field(default=0.0, init=False)
        _dbpool: adbapi.ConnectionPool | None = field(default=None, init=False)
        _busy: bool = field(default=False, init=False)
        _dbErrorCount: int = field(default=0, init=False)

    host: str
    database: str
    username: str
    password: str = field(repr=lambda _: "*")
    cacheInterval: int

    _state: _State = field(factory=_State, init=False, repr=False)

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
                from .test.dummy import DummyConnectionPool

                dbpool = cast(adbapi.ConnectionPool, DummyConnectionPool("Dummy"))

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

        sql = """
        select id, title from position where all_rangers = 0
        """
        self._log.debug("EXECUTE DMS: {sql}", sql=sql)
        rows = await self.dbpool.runQuery(sql)

        return {id: Position(positionID=id, name=title) for (id, title) in rows}

    async def _queryTeamsByID(self) -> Mapping[str, Team]:
        self._log.info("Retrieving teams from Duty Management System...")

        sql = """
        select id, title from team
        """
        self._log.debug("EXECUTE DMS: {sql}", sql=sql)
        rows = await self.dbpool.runQuery(sql)

        return {id: Team(teamID=id, name=title) for (id, title) in rows}

    async def _queryRangersByID(self) -> Mapping[str, Ranger]:
        self._log.info("Retrieving personnel from Duty Management System...")

        sql = """
        select
            id,
            callsign,
            email,
            status,
            on_site,
            password
        from person
        where status in ('active', 'inactive', 'vintage', 'auditor')
        """
        self._log.debug("EXECUTE DMS: {sql}", sql=sql)
        rows = await self.dbpool.runQuery(sql)

        return {
            directoryID: Ranger(
                handle=handle,
                status=statusFromID(status),
                email=(email,),
                onsite=bool(onsite),
                directoryID=directoryID,
                password=password,
            )
            for (
                directoryID,
                handle,
                email,
                status,
                onsite,
                password,
            ) in rows
        }

    async def _queryPositionRangerJoin(self) -> Iterable[tuple[str, str]]:
        self._log.info(
            "Retrieving position-personnel relations from Duty Management System..."
        )

        return cast(
            Iterable[tuple[str, str]],
            await self.dbpool.runQuery(
                """
                select person_id, position_id from person_position
                """
            ),
        )

    async def _queryTeamRangerJoin(self) -> Iterable[tuple[str, str]]:
        self._log.info(
            "Retrieving team-personnel relations from Duty Management System..."
        )

        return cast(
            Iterable[tuple[str, str]],
            await self.dbpool.runQuery(
                """
                select person_id, team_id from person_team
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

    async def teams(self) -> Iterable[Team]:
        """
        Look up all teams.
        """
        await self.personnel()
        return self._state._teams

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
                    positionJoin = await self._queryPositionRangerJoin()
                    teamsByID = await self._queryTeamsByID()
                    teamJoin = await self._queryTeamRangerJoin()

                    for rangerID, positionID in positionJoin:
                        position = positionsByID.get(positionID, None)
                        if position is None:
                            continue
                        ranger = rangersByID.get(rangerID, None)
                        if ranger is None:
                            continue
                        position.members.add(ranger)

                    for rangerID, teamID in teamJoin:
                        team = teamsByID.get(teamID, None)
                        if team is None:
                            continue
                        ranger = rangersByID.get(rangerID, None)
                        if ranger is None:
                            continue
                        team.members.add(ranger)

                    self._state._personnel = tuple(rangersByID.values())
                    self._state._positions = tuple(positionsByID.values())
                    self._state._teams = tuple(teamsByID.values())
                    self._state._personnelLastUpdated = time()
                    self._state._dbErrorCount = 0

                except Exception as e:
                    self._state._personnelLastUpdated = 0
                    self._state._dbpool = None
                    self._state._dbErrorCount += 1

                    if isinstance(e, SQLDatabaseError | SQLOperationalError):
                        if self._state._dbErrorCount < 2:  # noqa: PLR2004
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
                        self._log.failure("Unable to load personnel data from DMS")

                    # Try 2 times before raising an error
                    if elapsed > self.cacheInterval * 2:
                        raise DatabaseError(
                            f"Unable to load expired personnel data from DMS: {e}"
                        ) from e

            finally:
                self._state._busy = False

        try:
            return self._state._personnel
        except AttributeError:
            raise DMSError("No personnel data loaded.") from None


def statusFromID(strValue: str) -> RangerStatus:
    return {
        "active": RangerStatus.active,
        "inactive": RangerStatus.inactive,
        "vintage": RangerStatus.vintage,
    }.get(strValue, RangerStatus.other)
