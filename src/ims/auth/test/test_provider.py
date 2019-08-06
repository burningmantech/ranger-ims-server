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
Tests for L{ims.auth._provider}.
"""

from typing import Any
from unittest.mock import patch

from hypothesis import assume, given
from hypothesis.strategies import text

from ims.dms import DutyManagementSystem, hashPassword
from ims.ext.trial import TestCase
from ims.model import Ranger
from ims.model.strategies import rangers
from ims.store import IMSDataStore
from ims.store.sqlite import DataStore as SQLiteDataStore

from .._provider import AuthProvider, Authorization, User


__all__ = ()



class AuthorizationTests(TestCase):
    """
    Tests for :class:`Authorization`
    """

    def test_authorization_none(self) -> None:
        for authorization in Authorization:
            if authorization is Authorization.none:
                continue
            self.assertNotIn(authorization, Authorization.none)


    def test_authorization_all(self) -> None:
        for authorization in Authorization:
            self.assertIn(authorization, Authorization.all)



class UserTests(TestCase):
    """
    Tests for :class:`User`
    """

    @given(rangers())
    def test_shortNames_handle(self, ranger: Ranger) -> None:
        user = User(ranger=ranger, groups=())
        self.assertIn(ranger.handle, user.shortNames)


    @given(rangers())
    def test_hashedPassword(self, ranger: Ranger) -> None:
        user = User(ranger=ranger, groups=())
        self.assertEqual(user.hashedPassword, ranger.password)


    @given(rangers())
    def test_active(self, ranger: Ranger) -> None:
        user = User(ranger=ranger, groups=())
        self.assertEqual(user.active, ranger.onSite)


    @given(rangers())
    def test_rangerHandle(self, ranger: Ranger) -> None:
        user = User(ranger=ranger, groups=())
        self.assertEqual(user.rangerHandle, ranger.handle)


    @given(rangers())
    def test_str(self, ranger: Ranger) -> None:
        user = User(ranger=ranger, groups=())
        self.assertEqual(str(user), str(ranger))


class AuthProviderTests(TestCase):
    """
    Tests for :class:`AuthProvider`
    """

    def store(self) -> IMSDataStore:
        return SQLiteDataStore(dbPath=None)


    def dms(self) -> DutyManagementSystem:
        """
        Gimme a DMS.
        """
        return DutyManagementSystem(
            host="dms-server",
            database="ims",
            username="user",
            password="password",
        )


    @given(text(min_size=1), rangers())
    def test_verifyCredentials_masterKey(
        self, masterKey: str, ranger: Ranger
    ) -> None:
        provider = AuthProvider(
            store=self.store(), dms=self.dms(), masterKey=masterKey
        )
        user = User(ranger=ranger, groups=())

        authorization = self.successResultOf(
            provider.verifyCredentials(user, masterKey)
        )
        self.assertTrue(authorization)


    @given(rangers(), text())
    def test_verifyCredentials_match(
        self, ranger: Ranger, password: str
    ) -> None:
        provider = AuthProvider(store=self.store(), dms=self.dms())
        ranger = ranger.replace(password=hashPassword(password))
        user = User(ranger=ranger, groups=())

        authorization = self.successResultOf(
            provider.verifyCredentials(user, password)
        )
        self.assertTrue(authorization)


    @given(rangers(), text(), text())
    def test_verifyCredentials_mismatch(
        self, ranger: Ranger, password: str, otherPassword: str
    ) -> None:
        assume(password != otherPassword)

        provider = AuthProvider(store=self.store(), dms=self.dms())
        ranger = ranger.replace(password=hashPassword(password))
        user = User(ranger=ranger, groups=())

        authorization = self.successResultOf(
            provider.verifyCredentials(user, otherPassword)
        )
        self.assertFalse(authorization)


    @given(rangers(), text())
    def test_verifyCredentials_none(
        self, ranger: Ranger, password: str
    ) -> None:
        provider = AuthProvider(store=self.store(), dms=self.dms())
        ranger = ranger.replace(password=None)
        user = User(ranger=ranger, groups=())

        authorization = self.successResultOf(
            provider.verifyCredentials(user, password)
        )
        self.assertFalse(authorization)


    @given(rangers(), text())
    def test_verifyCredentials_error(
        self, ranger: Ranger, password: str
    ) -> None:
        provider = AuthProvider(store=self.store(), dms=self.dms())
        ranger = ranger.replace(password=hashPassword(password))
        user = User(ranger=ranger, groups=())

        def oops(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError()

        assert self.successResultOf(
            provider.verifyCredentials(user, password)
        )

        with patch("ims.auth._provider.verifyPassword", oops):
            authorization = self.successResultOf(
                provider.verifyCredentials(user, password)
            )
        self.assertFalse(authorization)
