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
Tests for L{ims.directory._directory}.
"""

from typing import Any, Callable, Dict, Iterable, Sequence, cast
from unittest.mock import patch

from attr import evolve

from hypothesis import assume, example, given
from hypothesis.strategies import composite, iterables, lists, text

from ims.ext.trial import TestCase
from ims.model import Ranger, RangerStatus
from ims.model.strategies import rangerHandles, rangers

from .._directory import (
    DirectoryError,
    IMSGroupID,
    RangerDirectory,
    RangerUser,
    hashPassword,
)


__all__ = ()


@composite
def groupIDs(draw: Callable) -> Iterable[IMSGroupID]:
    return cast(
        Iterable[IMSGroupID], iterables(IMSGroupID(draw(text(min_size=1)))),
    )


@composite
def uniqueRangerLists(draw: Callable) -> RangerDirectory:
    return cast(
        RangerDirectory, draw(lists(rangers(), unique_by=lambda r: r.handle)),
    )


@composite
def rangerUsers(draw: Callable) -> RangerUser:
    return RangerUser(ranger=draw(rangers()), groups=draw(groupIDs()),)


class RangerUserTests(TestCase):
    """
    Tests for :class:`RangerUser`
    """

    @given(rangerUsers())
    def test_str(self, user: RangerUser) -> None:
        self.assertEqual(str(user), str(user.ranger))

    @given(rangerUsers())
    def test_shortNames_handle(self, user: RangerUser) -> None:
        """
        Ranger handle is in user short names.
        """
        self.assertIn(user.ranger.handle, user.shortNames)

    @given(rangerUsers())
    def test_active(self, user: RangerUser) -> None:
        """
        Ranger on site status is used to set user active status.
        """
        self.assertEqual(user.active, user.ranger.enabled)

    @given(rangerUsers())
    def test_uid(self, user: RangerUser) -> None:
        """
        Ranger handle is used as user UID.
        """
        self.assertEqual(user.uid, user.ranger.handle)

    @given(rangerUsers())
    def test_groups(self, user: RangerUser) -> None:
        """
        User groups are as provided.
        """
        self.assertEqual(user.groups, user._groups)

    @given(rangerUsers(), text())
    def test_verifyPassword_match(
        self, user: RangerUser, password: str
    ) -> None:
        """
        RangerUser.verifyPassword() returns True when the Ranger's password is a
        match.
        """
        ranger = user.ranger.replace(password=hashPassword(password))
        user = evolve(user, ranger=ranger)

        authorization = self.successResultOf(user.verifyPassword(password))
        self.assertTrue(authorization)

    @given(rangerUsers(), text(), text())
    def test_verifyPassword_mismatch(
        self, user: RangerUser, password: str, otherPassword: str
    ) -> None:
        """
        RangerUser.verifyPassword() returns False when the Ranger's password is
        not a match.
        """
        assume(password != otherPassword)

        ranger = user.ranger.replace(password=hashPassword(password))
        user = evolve(user, ranger=ranger)

        authorization = self.successResultOf(user.verifyPassword(otherPassword))
        self.assertFalse(authorization)

    @given(rangerUsers(), text())
    def test_verifyPassword_none(self, user: RangerUser, password: str) -> None:
        """
        RangerUser.verifyPassword() returns False when the Ranger's password is
        None.
        """
        ranger = user.ranger.replace(password=None)
        user = evolve(user, ranger=ranger)

        authorization = self.successResultOf(user.verifyPassword(password))
        self.assertFalse(authorization)

    @given(rangerUsers(), text(), text())
    def test_verifyPassword_error(
        self, user: RangerUser, password: str, message: str
    ) -> None:
        """
        RangerUser.verifyPassword() returns False when verifyPassword raises an
        exception.
        """
        ranger = user.ranger.replace(password=hashPassword(password))
        user = evolve(user, ranger=ranger)

        def oops(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError(message)

        assert self.successResultOf(user.verifyPassword(password))

        with patch("ims.directory._directory.verifyPassword", oops):
            f = self.failureResultOf(
                user.verifyPassword(password), DirectoryError
            )
            self.assertEqual(
                f.getErrorMessage(), f"Unable to verify password: {message}"
            )


class DirectoryTests(TestCase):
    """
    Tests for :class:`Directory`
    """

    @given(uniqueRangerLists())
    def test_validateRangers_ok(self, rangers: Sequence[Ranger]) -> None:
        """
        RangerDirectory initializer validates the given (valid) Rangers without
        error.
        """
        RangerDirectory(rangers=rangers, positions=())

    @given(uniqueRangerLists(), lists(rangers(), min_size=2), rangerHandles())
    def test_validateRangers_duplicateHandle(
        self,
        rangers: Sequence[Ranger],
        duplicateRangers: Sequence[Ranger],
        duplicateHandle: str,
    ) -> None:
        """
        RangerDirectory initializer validates the given Rangers with duplicate
        handles and raises DirectoryError.
        """
        duplicateRangers = [
            evolve(ranger, handle=duplicateHandle)
            for ranger in duplicateRangers
        ]
        rangers = tuple(rangers) + tuple(duplicateRangers)

        e = self.assertRaises(
            DirectoryError, RangerDirectory, rangers=rangers, positions=()
        )
        self.assertEqual(str(e), f"Duplicate Ranger handle: {duplicateHandle}")

    @given(uniqueRangerLists())
    def test_personnel(self, rangers: Sequence[Ranger]) -> None:
        """
        RangerDirectory.personnel() returns all Rangers.
        """
        directory = RangerDirectory(rangers=rangers, positions=())
        personnel = self.successResultOf(directory.personnel())

        self.assertEqual(frozenset(personnel), frozenset(rangers))

    @given(uniqueRangerLists())
    def test_lookupUser_handle(self, rangers: Sequence[Ranger]) -> None:
        directory = RangerDirectory(rangers=rangers, positions=())

        for ranger in rangers:
            user = self.successResultOf(directory.lookupUser(ranger.handle))
            self.assertIsNotNone(user)
            self.assertEqual(user.ranger.handle, ranger.handle)

    @given(uniqueRangerLists())
    @example(
        [
            Ranger(
                handle="A",
                name="A",
                status=RangerStatus.active,
                email="same@example.com",
                enabled=True,
                directoryID="0",
                password=None,
            ),
            Ranger(
                handle="B",
                name="B",
                status=RangerStatus.active,
                email="same@example.com",
                enabled=True,
                directoryID="1",
                password=None,
            ),
            Ranger(
                handle="C",
                name="C",
                status=RangerStatus.active,
                email="same@example.com",
                enabled=True,
                directoryID="2",
                password=None,
            ),
        ]
    )
    def test_lookupUser_email(self, rangers: Sequence[Ranger]) -> None:
        directory = RangerDirectory(rangers=rangers, positions=())

        emailCounts: Dict[str, int] = dict()
        for ranger in rangers:
            for email in ranger.email:
                emailCounts[email] = emailCounts.get(email, 0) + 1

        for ranger in rangers:
            for email in ranger.email:
                user = self.successResultOf(directory.lookupUser(email))
                if user is None:
                    self.assertGreater(emailCounts[email], 0)
                else:
                    self.assertEqual(user.ranger.handle, ranger.handle)
