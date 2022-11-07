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

from collections.abc import Callable, Iterable, Sequence
from typing import Any, cast

from attrs import evolve
from hypothesis import example, given
from hypothesis.strategies import composite, iterables, lists, text

from ims.ext.trial import TestCase
from ims.model import Ranger, RangerStatus
from ims.model.strategies import rangerHandles, rangers

from .._directory import (
    DirectoryError,
    IMSGroupID,
    IMSUser,
    RangerDirectory,
    _hash,
    hashPassword,
    userFromRanger,
    verifyPassword,
)


__all__ = ()


@composite
def groupIDs(draw: Callable[..., Any]) -> Iterable[IMSGroupID]:
    return cast(
        Iterable[IMSGroupID],
        iterables(IMSGroupID(draw(text(min_size=1)))),
    )


@composite
def uniqueRangerLists(draw: Callable[..., Any]) -> RangerDirectory:
    return cast(
        RangerDirectory,
        draw(lists(rangers(), unique_by=lambda r: r.handle)),
    )


@composite
def imsUsers(draw: Callable[..., Any]) -> IMSUser:
    return userFromRanger(
        ranger=draw(rangers()),
        groups=draw(groupIDs()),
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

        emailCounts: dict[str, int] = {}
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


class UtilityTests(TestCase):
    """
    Tests for utilities.
    """

    @given(text())
    def test_hashPassword_noSalt(self, password: str) -> None:
        hashedPassword = hashPassword(password)
        saltOut, hashOut = hashedPassword.rsplit(":", 1)

        self.assertGreater(len(saltOut), 0)
        self.assertEqual(len(hashOut), 40)
        self.assertEqual(hashOut, _hash(password, saltOut))
        self.assertNotEqual(password, hashOut)

    @given(text(), text())
    def test_hashPassword_salt(self, password: str, salt: str) -> None:
        hashedPassword = hashPassword(password, salt)
        saltOut, hashOut = hashedPassword.rsplit(":", 1)

        self.assertEqual(saltOut, salt)
        self.assertEqual(len(hashOut), 40)
        self.assertEqual(hashOut, _hash(password, salt))
        self.assertNotEqual(password, hashOut)

    @given(text())
    def test_verifyPassword_noSalt(self, password: str) -> None:
        hashedPassword = hashPassword(password)
        self.assertTrue(verifyPassword(password, hashedPassword))

    @given(text(), text())
    def test_verifyPassword_salt(self, password: str, salt: str) -> None:
        hashedPassword = hashPassword(password, salt)
        self.assertTrue(verifyPassword(password, hashedPassword))

    @given(text(), text().filter(lambda s: ":" not in s))
    def test_verifyPassword_invalidHash(
        self, password: str, hashedPassword: str
    ) -> None:
        self.assertRaises(ValueError, verifyPassword, password, hashedPassword)
