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
Incident Management System directory service integration.
"""

from abc import ABC, abstractmethod
from hashlib import sha1
from typing import Dict, Iterable, NewType, Optional, Sequence, Set

from attr import Factory, attrs

from ims.model import Ranger


__all__ = ()


IMSUserID = NewType("IMSUserID", str)
IMSGroupID = NewType("IMSGroupID", str)


@attrs(frozen=False, auto_attribs=True, auto_exc=True)
class DirectoryError(Exception):
    """
    Directory service error.
    """

    message: str


class IMSUser(ABC):
    """
    IMS user
    """

    @property
    @abstractmethod
    def uid(self) -> IMSUserID:
        """
        Unique identifier.
        """

    @property
    @abstractmethod
    def shortNames(self) -> Sequence[str]:
        """
        Short names (usernames).
        """

    @property
    @abstractmethod
    def active(self) -> bool:
        """
        Whether the user is allowed to log in to the IMS.
        """

    @property
    @abstractmethod
    def groups(self) -> Sequence[IMSGroupID]:
        """
        Groups the user is a member of.
        """

    @abstractmethod
    async def verifyPassword(self, password: str) -> bool:
        """
        Verify whether a password is valid for the user.
        """


class IMSDirectory(ABC):
    """
    IMS directory service.
    """

    async def lookupUser(self, searchTerm: str) -> Optional[IMSUser]:
        """
        Look up a user given a text search term.
        """

    async def personnel(self) -> Iterable[Ranger]:
        """
        Look up all personnel.
        """


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class RangerUser(IMSUser):
    """
    IMS user derived from a Ranger.
    """

    ranger: Ranger
    _groups: Sequence[IMSGroupID]

    def __str__(self) -> str:
        return str(self.ranger)

    @property
    def uid(self) -> IMSUserID:
        """
        Unique identifier.
        """
        return IMSUserID(self.ranger.handle)

    @property
    def shortNames(self) -> Sequence[str]:
        """
        Short names (i.e. usernames).
        """
        return (self.ranger.handle,)

    @property
    def active(self) -> bool:
        """
        Whether the user is allowed to log in to the IMS.
        """
        return self.ranger.enabled

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
        hashedPassword = self.ranger.password
        if hashedPassword is None:
            return False
        else:
            try:
                return verifyPassword(password, hashedPassword)
            except Exception as e:
                raise DirectoryError(f"Unable to verify password: {e}")


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class RangerDirectory(IMSDirectory):
    """
    IMS directory derived from a sequence of Rangers.
    """

    _rangers: Sequence[Ranger]
    _usersByHandle: Dict[str, RangerUser] = Factory(dict)
    _usersByEmail: Dict[str, RangerUser] = Factory(dict)

    def __attrs_post_init__(self) -> None:
        usersByHandle = self._usersByHandle
        usersByEmail = self._usersByEmail
        duplicateEmails: Set[str] = set()

        for ranger in self._rangers:
            if ranger.handle in usersByHandle:
                raise DirectoryError(
                    f"Duplicate Ranger handle: {ranger.handle}"
                )
            user = RangerUser(ranger=ranger, groups=())

            usersByHandle[ranger.handle] = user

            for email in ranger.email:
                if email in duplicateEmails:
                    continue
                if email in usersByEmail:
                    duplicateEmails.add(email)
                    del usersByEmail[email]
                    continue
                usersByEmail[email] = user

    async def personnel(self) -> Iterable[Ranger]:
        return self._rangers

    async def lookupUser(self, searchTerm: str) -> Optional[IMSUser]:
        user = self._usersByHandle.get(searchTerm)
        if user is not None:
            return user

        user = self._usersByEmail.get(searchTerm)
        if user is not None:
            return user

        return None


def hashPassword(password: str, salt: str) -> str:
    """
    Compute a hash for the given password
    """
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
