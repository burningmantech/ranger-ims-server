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

from collections.abc import Callable, Sequence
from typing import Any, Callable

from attr import attrs, evolve
from hypothesis import assume, given
from hypothesis.strategies import booleans, composite, lists, none, one_of, text
from jwcrypto.jwk import JWK

from ims.ext.trial import TestCase
from ims.store import IMSDataStore
from ims.store.sqlite import DataStore as SQLiteDataStore

from ...directory import IMSGroupID, IMSUser, IMSUserID
from .._provider import Authorization, AuthProvider


__all__ = ()


def oops(*args: Any, **kwargs: Any) -> None:
    raise AssertionError()


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class TestUser(IMSUser):
    """
    User for testing.
    """

    _shortNames: Sequence[str]
    _active: bool
    _uid: IMSUserID
    _groups: Sequence[IMSGroupID]
    _password: str | None

    def __str__(self) -> str:
        return str(self._shortNames[0])

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


@composite
def testUsers(draw: Callable[..., Any]) -> TestUser:
    return TestUser(
        uid=IMSUserID(draw(text(min_size=1))),
        shortNames=tuple(draw(lists(text(min_size=1), min_size=1))),
        active=draw(booleans()),
        groups=tuple(IMSGroupID(g) for g in draw(text(min_size=1))),
        password=draw(one_of(none(), text())),
    )


@composite
def authorizations(draw: Callable[..., Any]) -> Authorization:
    """
    Strategy that generates :class:`Authorization` values.
    """
    authorization = Authorization.none
    for subAuthorization in draw(sets(Authorization, max_size=len(Authorization))):
        authorization |= subAuthorization
    return authorization


class TestTests(TestCase):
    """
    Tests for tests, because meta.
    """

    def test_oops(self) -> None:
        self.assertRaises(AssertionError, oops)

    @given(
        text(min_size=1),
        lists(text(min_size=1), min_size=1),
        booleans(),
        lists(text(min_size=1)),
        text(),
    )
    def test_testUser(
        self,
        _uid: str,
        shortNames: Sequence[str],
        active: bool,
        _groups: Sequence[str],
        password: str,
    ) -> None:
        uid = IMSUserID(_uid)
        groups = tuple(IMSGroupID(g) for g in _groups)

        user = TestUser(
            uid=uid,
            shortNames=shortNames,
            active=active,
            groups=groups,
            password=password,
        )

        self.assertEqual(tuple(user.shortNames), tuple(shortNames))
        self.assertEqual(user.active, active)
        self.assertEqual(user.uid, uid)
        self.assertEqual(tuple(user.groups), tuple(groups))

        self.assertTrue(self.successResultOf(user.verifyPassword(password)))


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
        testUsers(),
        text(min_size=1),
    )
    def test_verifyPassword_masterKey(
        self, user: TestUser, masterKey: str
    ) -> None:
        provider = AuthProvider(store=self.store(), masterKey=masterKey)

        authenticated = self.successResultOf(
            provider.verifyPassword(user, masterKey)
        )
        self.assertTrue(authenticated)

    @given(testUsers())
    def test_verifyPassword_match(self, user: TestUser) -> None:
        """
        AuthProvider.verifyPassword() returns True when the user's password is
        a match.
        """
        assume(user._password is not None)
        assert user._password is not None

        provider = AuthProvider(store=self.store())

        authenticated = self.successResultOf(
            provider.verifyPassword(user, user._password)
        )
        self.assertTrue(authenticated)

    @given(testUsers(), text())
    def test_verifyPassword_mismatch(
        self, user: TestUser, notPassword: str
    ) -> None:
        """
        AuthProvider.verifyPassword() returns False when the user's password is
        not a match.
        """
        assume(user._password != notPassword)

        provider = AuthProvider(store=self.store())

        authenticated = self.successResultOf(
            provider.verifyPassword(user, notPassword)
        )
        self.assertFalse(authenticated)

    @given(testUsers(), text())
    def test_verifyPassword_none(self, user: TestUser, password: str) -> None:
        """
        AuthProvider.verifyPassword() returns False when the user's password is
        None.
        """
        user = evolve(user, password=None)
        provider = AuthProvider(store=self.store())

        authenticated = self.successResultOf(
            provider.verifyPassword(user, password)
        )
        self.assertFalse(authenticated)

    def test_authenticateRequest(self) -> None:
        raise NotImplementedError()

    test_authenticateRequest.todo = (  # type: ignore[attr-defined]
        "unimplemented"
    )

    def test_jwtSecret(self) -> None:
        """
        AuthProvider._jwtSecret generates a JWT secret.
        """
        provider = AuthProvider(store=self.store())

        self.assertIsInstance(provider._jwtSecret, JWK)

    def test_jwtSecret_same(self) -> None:
        """
        AuthProvider._jwtSecret is the same secret.
        """
        provider = AuthProvider(store=self.store())

        self.assertIdentical(provider._jwtSecret, provider._jwtSecret)

    def test_matchACL_none_noUser(self) -> None:
        """
        AuthProvider._matchACL does not match no access with None user.
        """
        provider = AuthProvider(store=self.store())

        self.assertFalse(provider._matchACL(None, []))

    @given(testUsers())
    def test_matchACL_none_user(self, user: TestUser) -> None:
        """
        AuthProvider._matchACL does not match no access with a user.
        """
        provider = AuthProvider(store=self.store())

        self.assertFalse(provider._matchACL(user, []))

    def test_matchACL_public_noUser(self) -> None:
        """
        AuthProvider._matchACL matches public ("**") access with None user.
        """
        provider = AuthProvider(store=self.store())

        self.assertTrue(provider._matchACL(None, ["**"]))

    @given(testUsers())
    def test_matchACL_public_user(self, user: TestUser) -> None:
        """
        AuthProvider._matchACL matches public ("**") access with a user.
        """
        provider = AuthProvider(store=self.store())

        self.assertTrue(provider._matchACL(user, ["**"]))

    def test_matchACL_any_noUser(self) -> None:
        """
        AuthProvider._matchACL does not match any ("*") access with None user.
        """
        provider = AuthProvider(store=self.store(), requireActive=False)

        self.assertFalse(provider._matchACL(None, ["*"]))

    @given(testUsers())
    def test_matchACL_any_user(self, user: TestUser) -> None:
        """
        AuthProvider._matchACL matches any ("*") access with a user.
        """
        provider = AuthProvider(store=self.store(), requireActive=False)

        self.assertTrue(provider._matchACL(user, ["*"]))

    @given(testUsers())
    def test_matchACL_person(self, user: TestUser) -> None:
        """
        AuthProvider._matchACL matches person access with a matching user.
        """
        provider = AuthProvider(store=self.store(), requireActive=False)

        for shortName in user.shortNames:
            self.assertTrue(provider._matchACL(user, [f"person:{shortName}"]))

    @given(testUsers())
    def test_matchACL_position(self, user: TestUser) -> None:
        """
        AuthProvider._matchACL matches group access with a matching user.
        """
        provider = AuthProvider(store=self.store(), requireActive=False)

        for groupID in user.groups:
            self.assertTrue(provider._matchACL(user, [f"position:{groupID}"]))

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
