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
from typing import NewType, Protocol, cast

from attrs import field, frozen, mutable
from bcrypt import gensalt

from ims.model import Position, Ranger, Team


__all__ = ()


IMSUserID = NewType("IMSUserID", str)
IMSGroupID = NewType("IMSGroupID", str)
IMSTeamID = NewType("IMSTeamID", str)


@mutable
class DirectoryError(Exception):
    """
    Directory service error.
    """

    message: str


class IMSUser(Protocol):
    """
    IMS user.
    """

    uid: IMSUserID
    shortNames: Sequence[str]
    onsite: bool
    groups: Sequence[IMSGroupID]
    teams: Sequence[IMSTeamID]
    hashedPassword: str | None


@frozen(kw_only=True)
class DirectoryUser(IMSUser):
    """
    IMS user derived from a JWT payload.
    """

    uid: IMSUserID
    shortNames: Sequence[str]
    onsite: bool
    groups: Sequence[IMSGroupID]
    teams: Sequence[IMSTeamID]
    hashedPassword: str | None = field(
        default=None, repr=lambda _p: "\N{ZIPPER-MOUTH FACE}"
    )


def userFromRanger(
    *, ranger: Ranger, groups: Sequence[IMSGroupID], teams: Sequence[IMSTeamID]
) -> IMSUser:
    """
    Create an IMS user from a Ranger.
    """
    return DirectoryUser(
        uid=IMSUserID(ranger.handle),
        shortNames=(ranger.handle,),
        onsite=ranger.onsite,
        groups=tuple(groups),
        teams=tuple(teams),
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

    def verifyPassword(self, user: IMSUser, password: str) -> bool:
        if user.hashedPassword is None:
            return False
        return verifyPassword(password, user.hashedPassword)


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
    _teamsByHandle: dict[str, Sequence[Team]] = field(factory=dict)

    def __attrs_post_init__(self) -> None:
        usersByHandle = self._usersByHandle
        usersByEmail = self._usersByEmail
        duplicateEmails: set[str] = set()

        for position in self._positions:
            for handle in position.members:
                cast(
                    "list[Position]",
                    self._positionsByHandle.setdefault(handle, []),
                ).append(position)

        for ranger in self._rangers:
            if ranger.handle in usersByHandle:
                raise DirectoryError(f"Duplicate Ranger handle: {ranger.handle}")
            groups = tuple(
                IMSGroupID(position.name)
                for position in self._positionsByHandle.get(ranger.handle, ())
            )
            teams = tuple(
                IMSTeamID(team.name)
                for team in self._teamsByHandle.get(ranger.handle, ())
            )
            user = userFromRanger(ranger=ranger, groups=groups, teams=teams)

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
    # FIXME: SHA1 is vulnerable; need to fix in Clubhouse
    return sha1((salt + password).encode("utf-8")).hexdigest()  # noqa: S324


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
