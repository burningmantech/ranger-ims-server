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

from hashlib import sha1
from os import urandom
from typing import ClassVar, Iterable, Optional, Sequence, cast

from attr import attrs

from twisted.logger import Logger

from ims.directory import IMSDirectory, IMSGroupID, IMSUser, IMSUserID
from ims.model import Ranger

from ._dms import DMSError, DutyManagementSystem


__all__ = ()


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class DMSUser(IMSUser):
    """
    IMS user derived from DMS Ranger.
    """

    _log: ClassVar[Logger] = Logger()

    _ranger: Ranger
    _groups: Sequence[IMSGroupID]

    def __str__(self) -> str:
        return str(self._ranger)

    @property
    def shortNames(self) -> Sequence[str]:
        """
        Short names (i.e. usernames).
        """
        return (self._ranger.handle,)

    @property
    def active(self) -> bool:
        """
        Whether the user is allowed to log in to the IMS.
        """
        return self._ranger.enabled

    @property
    def uid(self) -> IMSUserID:
        """
        Unique identifier.
        """
        return cast(IMSUserID, self._ranger.handle)

    @property
    def groups(self) -> Sequence[IMSGroupID]:
        """
        Groups the user is a member of.
        """
        return self._groups

    async def verifyPassword(self, password: str) -> bool:
        """
        Verify whether a password is valid for the user.
        """
        hashedPassword = self._ranger.password
        if hashedPassword is None:
            return False
        else:
            try:
                return verifyPassword(password, hashedPassword)
            except Exception as e:
                raise DMSError(f"Unable to verify password: {e}")


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class DMSDirectory(IMSDirectory):
    """
    IMS user provider that uses the DMS.
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
            cast(IMSGroupID, position.name)
            for position in positions
            if ranger in position.members
        )

        return DMSUser(ranger=ranger, groups=groups)


def hashPassword(password: str, salt: Optional[str] = None) -> str:
    """
    Compute a hash for the given password
    """
    if salt is None:
        salt = urandom(16).decode("charmap")

    return salt + ":" + sha1((salt + password).encode("utf-8")).hexdigest()


def verifyPassword(password: str, hashedPassword: str) -> bool:
    """
    Verify a password against a hashed password.
    """
    # Reference Clubhouse code: standard/controllers/security.php#L457

    # DMS password field is a salt and a SHA-1 hash (hex digest), separated by
    # ":".
    salt, hashValue = hashedPassword.rsplit(":", 1)

    hashed = sha1((salt + password).encode("utf-8")).hexdigest()

    return hashed == hashValue
