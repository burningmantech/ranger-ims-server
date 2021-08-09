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

from typing import ClassVar, Iterable, Optional

from attr import attrs
from twisted.logger import Logger

from ims.directory import IMSDirectory, IMSGroupID, IMSUser, RangerUser
from ims.model import Ranger

from ._dms import DMSError, DutyManagementSystem


__all__ = ()


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class DMSDirectory(IMSDirectory):
    """
    IMS directory that uses the DMS.
    """

    _log: ClassVar[Logger] = Logger()

    _dms: DutyManagementSystem

    async def personnel(self) -> Iterable[Ranger]:
        return tuple(await self._dms.personnel())

    async def lookupUser(self, searchTerm: str) -> Optional[IMSUser]:
        dms = self._dms

        # FIXME: a hash would be better (eg. rangersByHandle)
        try:
            rangers = tuple(await dms.personnel())
        except DMSError as e:
            self._log.critical("Unable to load personnel: {error}", error=e)
            return None

        for ranger in rangers:
            if ranger.handle == searchTerm:
                break
        else:
            for ranger in rangers:
                if searchTerm in ranger.email:
                    break
            else:
                return None

        positions = tuple(await dms.positions())

        groups = tuple(
            IMSGroupID(position.name)
            for position in positions
            if ranger in position.members
        )

        return RangerUser(ranger=ranger, groups=groups)
