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
Tests for L{ims.directory.clubhouse_db._directory}.
"""

from typing import Any, Sequence
from unittest.mock import patch

from hypothesis import assume, given
from hypothesis.strategies import lists, text

from ims.ext.trial import TestCase
from ims.model import Ranger
from ims.model.strategies import rangers
from ims.store import IMSDataStore
from ims.store.sqlite import DataStore as SQLiteDataStore

from .._directory import DMSUser, hashPassword
from .._dms import DMSError
from ..._directory import IMSGroupID


__all__ = ()


class DMSUserTests(TestCase):
    """
    Tests for :class:`User`
    """

    def store(self) -> IMSDataStore:
        return SQLiteDataStore(dbPath=None)

    @given(rangers(), lists(text()))
    def test_str(self, ranger: Ranger, groups: Sequence[IMSGroupID]) -> None:
        user = DMSUser(ranger=ranger, groups=groups)
        self.assertEqual(str(user), str(ranger))

    @given(rangers(), lists(text()))
    def test_shortNames_handle(
        self, ranger: Ranger, groups: Sequence[IMSGroupID]
    ) -> None:
        """
        Ranger handle is in user short names.
        """
        user = DMSUser(ranger=ranger, groups=groups)
        self.assertIn(ranger.handle, user.shortNames)

    @given(rangers(), lists(text()))
    def test_active(self, ranger: Ranger, groups: Sequence[IMSGroupID]) -> None:
        """
        Ranger on site status is used to set user active status.
        """
        user = DMSUser(ranger=ranger, groups=groups)
        self.assertEqual(user.active, ranger.enabled)

    @given(rangers(), lists(text()))
    def test_uid(self, ranger: Ranger, groups: Sequence[IMSGroupID]) -> None:
        """
        Ranger handle is used as user UID.
        """
        user = DMSUser(ranger=ranger, groups=groups)
        self.assertEqual(user.uid, ranger.handle)

    @given(rangers(), lists(text()))
    def test_groups(self, ranger: Ranger, groups: Sequence[IMSGroupID]) -> None:
        """
        User groups are as provided.
        """
        user = DMSUser(ranger=ranger, groups=groups)
        self.assertEqual(user.groups, groups)

    @given(rangers(), lists(text()), text())
    def test_verifyPassword_match(
        self, ranger: Ranger, groups: Sequence[IMSGroupID], password: str
    ) -> None:
        """
        DMSUser.verifyPassword() returns True when the Ranger's password is a
        match.
        """
        ranger = ranger.replace(password=hashPassword(password))
        user = DMSUser(ranger=ranger, groups=groups)

        authorization = self.successResultOf(user.verifyPassword(password))
        self.assertTrue(authorization)

    @given(rangers(), lists(text()), text(), text())
    def test_verifyPassword_mismatch(
        self,
        ranger: Ranger,
        groups: Sequence[IMSGroupID],
        password: str,
        otherPassword: str,
    ) -> None:
        """
        DMSUser.verifyPassword() returns False when the Ranger's password is
        not a match.
        """
        assume(password != otherPassword)

        ranger = ranger.replace(password=hashPassword(password))
        user = DMSUser(ranger=ranger, groups=groups)

        authorization = self.successResultOf(user.verifyPassword(otherPassword))
        self.assertFalse(authorization)

    @given(rangers(), lists(text()), text())
    def test_verifyPassword_none(
        self, ranger: Ranger, groups: Sequence[IMSGroupID], password: str
    ) -> None:
        """
        DMSUser.verifyPassword() returns False when the Ranger's password is
        None.
        """
        ranger = ranger.replace(password=None)
        user = DMSUser(ranger=ranger, groups=groups)

        authorization = self.successResultOf(user.verifyPassword(password))
        self.assertFalse(authorization)

    @given(rangers(), lists(text()), text(), text())
    def test_verifyPassword_error(
        self,
        ranger: Ranger,
        groups: Sequence[IMSGroupID],
        password: str,
        message: str,
    ) -> None:
        """
        DMSUser.verifyPassword() returns False when verifyPassword raises an
        exception.
        """
        ranger = ranger.replace(password=hashPassword(password))
        user = DMSUser(ranger=ranger, groups=groups)

        def oops(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError(message)

        assert self.successResultOf(user.verifyPassword(password))

        with patch(
            "ims.directory.clubhouse_db._directory.verifyPassword", oops
        ):
            f = self.failureResultOf(user.verifyPassword(password), DMSError)
            self.assertEqual(
                f.getErrorMessage(), f"Unable to verify password: {message}"
            )
