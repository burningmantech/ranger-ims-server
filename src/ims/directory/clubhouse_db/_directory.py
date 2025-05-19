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
Duty Management System directory.
"""

from collections.abc import Iterable
from typing import ClassVar

from attrs import frozen
from twisted.logger import Logger

from ims.directory import IMSDirectory, IMSGroupID, IMSTeamID, IMSUser, userFromRanger
from ims.model import Ranger

from ._dms import DutyManagementSystem, Position, Team


__all__ = ()


@frozen(kw_only=True)
class DMSDirectory(IMSDirectory):
    """
    IMS directory that uses the DMS.
    """

    _log: ClassVar[Logger] = Logger()

    _dms: DutyManagementSystem

    async def personnel(self) -> Iterable[Ranger]:
        return tuple(await self._dms.personnel())

    async def lookupUser(self, searchTerm: str) -> IMSUser | None:
        dms = self._dms
        # call out to a more easily testable static method
        return DMSDirectory._lookupUser(
            searchTerm,
            tuple(await dms.personnel()),
            tuple(await dms.positions()),
            tuple(await dms.teams()),
        )

    @staticmethod
    def _lookupUser(
        searchTerm: str,
        rangers: tuple[Ranger, ...],
        positions: tuple[Position, ...],
        teams: tuple[Team, ...],
    ) -> IMSUser | None:
        searchLower = searchTerm.lower()

        ranger = None

        for r in rangers:
            if r.handle.lower() == searchLower:
                ranger = r
            for email in r.email:
                if email and email.lower() == searchLower:
                    ranger = r
            if ranger is not None:
                break
        else:
            return None

        assert ranger is not None

        groups = tuple(
            IMSGroupID(position.name)
            for position in positions
            if ranger in position.members
        )

        imsTeams = tuple(
            IMSTeamID(team.name) for team in teams if ranger in team.members
        )

        return userFromRanger(ranger=ranger, groups=groups, teams=imsTeams)
