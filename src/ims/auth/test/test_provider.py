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

from typing import Any, Optional, Sequence

from attr import attrs

from hypothesis import assume, given
from hypothesis.strategies import booleans, lists, text

from ims.ext.trial import TestCase
from ims.store import IMSDataStore
from ims.store.sqlite import DataStore as SQLiteDataStore

from .._provider import AuthProvider, Authorization
from ...directory import IMSGroupID, IMSUser, IMSUserID


__all__ = ()


def oops(*args: Any, **kwargs: Any) -> None:
    raise RuntimeError()


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class TestUser(IMSUser):
    """
    User for testing.
    """

    _shortNames: Sequence[str]
    _active: bool
    _uid: IMSUserID
    _groups: Sequence[IMSGroupID]
    _password: Optional[str]

    @property
    def shortNames(self) -> Sequence[str]:
        """
        Short names (usernames).
        """
        return self._shortNames

    @property
    def active(self) -> bool:
        """
        Whether the user is allowed to log in to the IMS.
        """
        return self._active

    @property
    def uid(self) -> IMSUserID:
        """
        Unique identifier.
        """
        return self._uid

    @property
    def groups(self) -> Sequence[IMSGroupID]:
        """
        Groups the user is a member of.
        """
        return self._groups

    async def verifyPassword(self, password: str) -> bool:
        assert self._password is not None
        return password == self._password


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


class AuthProviderTests(TestCase):
    """
    Tests for :class:`AuthProvider`
    """

    def store(self) -> IMSDataStore:
        return SQLiteDataStore(dbPath=None)

    # @given(text(min_size=1), rangers())
    @given(
        lists(text()),
        booleans(),
        text(),
        lists(text()),
        text(),
        text(min_size=1),
    )
    def test_verifyPassword_masterKey(
        self,
        shortNames: Sequence[str],
        active: bool,
        uid: IMSUserID,
        groups: Sequence[IMSGroupID],
        password: str,
        masterKey: str,
    ) -> None:
        user = TestUser(
            shortNames=shortNames,
            active=active,
            uid=uid,
            groups=groups,
            password=password,
        )
        provider = AuthProvider(store=self.store(), masterKey=masterKey)

        authorization = self.successResultOf(
            provider.verifyPassword(user, masterKey)
        )
        self.assertTrue(authorization)

    @given(lists(text()), booleans(), text(), lists(text()), text())
    def test_verifyPassword_match(
        self,
        shortNames: Sequence[str],
        active: bool,
        uid: IMSUserID,
        groups: Sequence[IMSGroupID],
        password: str,
    ) -> None:
        """
        AuthProvider.verifyPassword() returns True when the user's password is
        a match.
        """
        user = TestUser(
            shortNames=shortNames,
            active=active,
            uid=uid,
            groups=groups,
            password=password,
        )
        provider = AuthProvider(store=self.store())

        authorization = self.successResultOf(
            provider.verifyPassword(user, password)
        )
        self.assertTrue(authorization)

    @given(lists(text()), booleans(), text(), lists(text()), text(), text())
    def test_verifyPassword_mismatch(
        self,
        shortNames: Sequence[str],
        active: bool,
        uid: IMSUserID,
        groups: Sequence[IMSGroupID],
        password: str,
        notPassword: str,
    ) -> None:
        """
        AuthProvider.verifyPassword() returns False when the user's password is
        not a match.
        """
        assume(password != notPassword)

        user = TestUser(
            shortNames=shortNames,
            active=active,
            uid=uid,
            groups=groups,
            password=password,
        )
        provider = AuthProvider(store=self.store())

        authorization = self.successResultOf(
            provider.verifyPassword(user, notPassword)
        )
        self.assertFalse(authorization)

    @given(lists(text()), booleans(), text(), lists(text()), text())
    def test_verifyPassword_none(
        self,
        shortNames: Sequence[str],
        active: bool,
        uid: IMSUserID,
        groups: Sequence[IMSGroupID],
        password: str,
    ) -> None:
        """
        AuthProvider.verifyPassword() returns False when the user's password is
        None.
        """
        user = TestUser(
            shortNames=shortNames,
            active=active,
            uid=uid,
            groups=groups,
            password=None,
        )
        provider = AuthProvider(store=self.store())

        authorization = self.successResultOf(
            provider.verifyPassword(user, password)
        )
        self.assertFalse(authorization)

    def test_authenticateRequest(self) -> None:
        raise NotImplementedError()

    test_authenticateRequest.todo = (  # type: ignore[attr-defined]
        "unimplemented"
    )

    def test_authorizationsForUser(self) -> None:
        raise NotImplementedError()

    test_authorizationsForUser.todo = (  # type: ignore[attr-defined]
        "unimplemented"
    )

    def test_authorizeRequest(self) -> None:
        raise NotImplementedError()

    test_authorizeRequest.todo = "unimplemented"  # type: ignore[attr-defined]

    def test_authorizeReqForIncidentReport(self) -> None:
        raise NotImplementedError()

    test_authorizeReqForIncidentReport.todo = (  # type: ignore[attr-defined]
        "unimplemented"
    )
