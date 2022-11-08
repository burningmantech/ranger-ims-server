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
from collections.abc import Iterable, Sequence
from hashlib import sha1
from typing import NewType, cast

from attrs import field, frozen, mutable
from bcrypt import gensalt

from ims.model import Position, Ranger


__all__ = ()


IMSUserID = NewType("IMSUserID", str)
IMSGroupID = NewType("IMSGroupID", str)


@mutable
class DirectoryError(Exception):
    """
    Directory service error.
    """

    message: str


@frozen(kw_only=True)
class IMSUser:
    """
    IMS user derived from a JWT payload.
    """

    uid: IMSUserID
    shortNames: Sequence[str]
    active: bool
    groups: Sequence[IMSGroupID]
    hashedPassword: str | None = None

    def verifyPassword(self, password: str) -> bool:
        """
        Verify whether a password is valid for the user.
        """
        if self.hashedPassword is None:
            return False
        else:
            try:
                return verifyPassword(password, self.hashedPassword)
            except Exception as e:
                raise DirectoryError(f"Unable to verify password: {e}") from e


def userFromRanger(*, ranger: Ranger, groups: Sequence[IMSGroupID]) -> IMSUser:
    """
    Create an IMS user from a Ranger.
    """
    return IMSUser(
        uid=IMSUserID(ranger.handle),
        shortNames=(ranger.handle,),
        active=ranger.enabled,
        groups=tuple(groups),
        hashedPassword=ranger.password,
    )


class IMSDirectory(ABC):
    """
    IMS directory service.
    """

    @abstractmethod
    async def lookupUser(self, searchTerm: str) -> IMSUser | None:
        """
        Look up a user given a text search term.
        """

    @abstractmethod
    async def personnel(self) -> Iterable[Ranger]:
        """
        Look up all personnel.
        """


@frozen(kw_only=True)
class RangerDirectory(IMSDirectory):
    """
    IMS directory derived from a sequence of Rangers.
    """

    _rangers: Sequence[Ranger]
    _positions: Sequence[Position]
    _usersByHandle: dict[str, IMSUser] = field(factory=dict)
    _usersByEmail: dict[str, IMSUser] = field(factory=dict)
    _positionsByHandle: dict[str, Sequence[Position]] = field(factory=dict)

    def __attrs_post_init__(self) -> None:
        usersByHandle = self._usersByHandle
        usersByEmail = self._usersByEmail
        duplicateEmails: set[str] = set()

        for position in self._positions:
            for handle in position.members:
                cast(
                    list[Position],
                    self._positionsByHandle.setdefault(handle, []),
                ).append(position)

        for ranger in self._rangers:
            if ranger.handle in usersByHandle:
                raise DirectoryError(
                    f"Duplicate Ranger handle: {ranger.handle}"
                )
            groups = tuple(
                IMSGroupID(position.name)
                for position in self._positionsByHandle.get(ranger.handle, ())
            )
            user = userFromRanger(ranger=ranger, groups=groups)

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

    async def lookupUser(self, searchTerm: str) -> IMSUser | None:
        user = self._usersByHandle.get(searchTerm)
        if user is not None:
            return user

        user = self._usersByEmail.get(searchTerm)
        if user is not None:
            return user

        return None


def _hash(password: str, salt: str) -> str:
    # SHA1 is vulnerable; need to fix in Clubhouse
    return sha1((salt + password).encode("utf-8")).hexdigest()  # nosec


def hashPassword(password: str, salt: str | None = None) -> str:
    """
    Compute a hash for the given password
    """
    if salt is None:
        salt = gensalt().decode("charmap")

    return salt + ":" + _hash(password, salt)


def verifyPassword(password: str, hashedPassword: str) -> bool:
    """
    Verify a password against a hashed password.
    """
    # Reference Clubhouse code: standard/controllers/security.php#L457

    # DMS password field is a salt and a SHA-1 hash (hex digest), separated by
    # ":".
    salt, hashValue = hashedPassword.rsplit(":", 1)

    hashed = _hash(password, salt)

    return hashed == hashValue
