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
from pathlib import Path
from typing import Any
from unittest.mock import patch

from attrs import evolve, frozen
from hypothesis import assume, given
from hypothesis.strategies import (
    booleans,
    composite,
    lists,
    none,
    one_of,
    sets,
    text,
)
from jwcrypto.jwk import JWK

from ims.directory import IMSDirectory
from ims.directory.file import FileDirectory
from ims.ext.trial import TestCase
from ims.store import IMSDataStore
from ims.store.sqlite import DataStore as SQLiteDataStore

from ...directory import IMSGroupID, IMSUser, IMSUserID
from .._exceptions import InvalidCredentialsError
from .._provider import Authorization, AuthProvider, JSONWebTokenClaims


__all__ = ()


def oops(*args: Any, **kwargs: Any) -> None:
    raise AssertionError()


@frozen(kw_only=True)
class TestUser(IMSUser):
    """
    User for testing.
    """

    def __str__(self) -> str:
        return str(self.shortNames[0])

    def verifyPassword(self, password: str) -> bool:
        assert self.hashedPassword is not None
        return password == self.hashedPassword


@composite
def testUsers(draw: Callable[..., Any]) -> IMSUser:
    return TestUser(
        uid=IMSUserID(draw(text(min_size=1))),
        shortNames=tuple(draw(lists(text(min_size=1), min_size=1))),
        active=draw(booleans()),
        groups=tuple(IMSGroupID(g) for g in draw(text(min_size=1))),
        hashedPassword=draw(one_of(none(), text())),
    )


@composite
def authorizations(draw: Callable[..., Any]) -> Authorization:
    """
    Strategy that generates :class:`Authorization` values.
    """
    authorization = Authorization.none
    for subAuthorization in draw(
        sets(Authorization, max_size=len(Authorization))
    ):
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
            hashedPassword=password,
        )

        self.assertEqual(user.uid, uid)
        self.assertEqual(tuple(user.shortNames), tuple(shortNames))
        self.assertEqual(user.active, active)
        self.assertEqual(tuple(user.groups), tuple(groups))

        self.assertTrue(user.verifyPassword(password))


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


class JSONWebTokenClaimsTests(TestCase):
    """
    Tests for :class:`JSONWebTokenClaims`
    """

    now = 100000000

    def test_now_float(self) -> None:
        self.assertEqual(JSONWebTokenClaims._now(self.now), self.now)

    def test_now_none(self) -> None:
        def time() -> float:
            return self.now

        with patch("ims.auth._provider.time", time):
            JSONWebTokenClaims._now(self.now)
            self.assertEqual(JSONWebTokenClaims._now(None), self.now)

    def token(self, **kwargs: Any) -> JSONWebTokenClaims:
        defaults: dict[str, Any] = dict(
            iss="my-issuer",
            iat=self.now - 100,
            exp=self.now + 100,
            sub="some-uid",
            preferred_username="some-user",
            ranger_on_site=True,
            ranger_positions="some-position,another-position",
        )
        defaults.update(kwargs)
        return JSONWebTokenClaims(**defaults)

    def test_validateIssuer(self) -> None:
        """
        JSONWebTokenClaims.validateIssuer catches incorrect issuer.
        """
        token = self.token()
        self.assertRaises(
            InvalidCredentialsError, token.validateIssuer, "some-other-issuer"
        )
        self.assertRaises(
            InvalidCredentialsError, token.validate, issuer="some-other-issuer"
        )

    def test_validateIssued(self) -> None:
        """
        JSONWebTokenClaims.validateIssued catches future issue time.
        """
        token = self.token(iat=self.now + 1)
        self.assertRaises(
            InvalidCredentialsError, token.validateIssued, now=self.now
        )
        self.assertRaises(InvalidCredentialsError, token.validate, now=self.now)

    def test_validateExpiration(self) -> None:
        """
        JSONWebTokenClaims.validateExpiration catches elapsed expiration time.
        """
        token = self.token(exp=self.now - 1)
        self.assertRaises(
            InvalidCredentialsError, token.validateExpiration, now=self.now
        )
        self.assertRaises(InvalidCredentialsError, token.validate, now=self.now)

    def test_validate(self) -> None:
        """
        JSONWebTokenClaims.validate with valid claim doesn't raise.
        """
        self.token().validate(issuer="my-issuer", now=self.now)


class AuthProviderTests(TestCase):
    """
    Tests for :class:`AuthProvider`
    """

    def store(self) -> IMSDataStore:
        return SQLiteDataStore(dbPath=None)

    def directory(self) -> IMSDirectory:
        path = (
            Path(__file__).parent.parent.parent
            / "file"
            / "test"
            / "directory.yaml"
        )
        return FileDirectory(path=path)

    # @given(text(min_size=1), rangers())
    @given(
        testUsers(),
        text(min_size=1),
    )
    def test_verifyPassword_masterKey(
        self, user: IMSUser, masterKey: str
    ) -> None:
        provider = AuthProvider(
            store=self.store(), directory=self.directory(), masterKey=masterKey
        )

        authenticated = self.successResultOf(
            provider.verifyPassword(user, masterKey)
        )
        self.assertTrue(authenticated)

    @given(testUsers())
    def test_verifyPassword_match(self, user: IMSUser) -> None:
        """
        AuthProvider.verifyPassword() returns True when the user's password is
        a match.
        """
        assume(user.hashedPassword is not None)
        assert user.hashedPassword is not None

        provider = AuthProvider(store=self.store(), directory=self.directory())

        authenticated = self.successResultOf(
            provider.verifyPassword(user, user.hashedPassword)
        )
        self.assertTrue(authenticated)

    @given(testUsers(), text())
    def test_verifyPassword_mismatch(
        self, user: IMSUser, notPassword: str
    ) -> None:
        """
        AuthProvider.verifyPassword() returns False when the user's password is
        not a match.
        """
        assume(user.hashedPassword != notPassword)

        provider = AuthProvider(store=self.store(), directory=self.directory())

        authenticated = self.successResultOf(
            provider.verifyPassword(user, notPassword)
        )
        self.assertFalse(authenticated)

    @given(testUsers(), text())
    def test_verifyPassword_none(self, user: IMSUser, password: str) -> None:
        """
        AuthProvider.verifyPassword() returns False when the user's password is
        None.
        """
        user = evolve(user, hashedPassword=None)
        provider = AuthProvider(store=self.store(), directory=self.directory())

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
        provider = AuthProvider(store=self.store(), directory=self.directory())

        self.assertIsInstance(provider._jwtSecret, JWK)

    def test_jwtSecret_same(self) -> None:
        """
        AuthProvider._jwtSecret is the same secret.
        """
        provider = AuthProvider(store=self.store(), directory=self.directory())

        self.assertIdentical(provider._jwtSecret, provider._jwtSecret)

    def test_matchACL_none_noUser(self) -> None:
        """
        AuthProvider._matchACL does not match no access with None user.
        """
        provider = AuthProvider(store=self.store(), directory=self.directory())

        self.assertFalse(provider._matchACL(None, []))

    @given(testUsers())
    def test_matchACL_none_user(self, user: IMSUser) -> None:
        """
        AuthProvider._matchACL does not match no access with a user.
        """
        provider = AuthProvider(store=self.store(), directory=self.directory())

        self.assertFalse(provider._matchACL(user, []))

    def test_matchACL_public_noUser(self) -> None:
        """
        AuthProvider._matchACL matches public ("**") access with None user.
        """
        provider = AuthProvider(store=self.store(), directory=self.directory())

        self.assertTrue(provider._matchACL(None, ["**"]))

    @given(testUsers())
    def test_matchACL_public_user(self, user: IMSUser) -> None:
        """
        AuthProvider._matchACL matches public ("**") access with a user.
        """
        provider = AuthProvider(store=self.store(), directory=self.directory())

        self.assertTrue(provider._matchACL(user, ["**"]))

    def test_matchACL_any_noUser(self) -> None:
        """
        AuthProvider._matchACL does not match any ("*") access with None user.
        """
        provider = AuthProvider(
            store=self.store(), directory=self.directory(), requireActive=False
        )

        self.assertFalse(provider._matchACL(None, ["*"]))

    @given(testUsers())
    def test_matchACL_any_user(self, user: IMSUser) -> None:
        """
        AuthProvider._matchACL matches any ("*") access with a user.
        """
        provider = AuthProvider(
            store=self.store(), directory=self.directory(), requireActive=False
        )

        self.assertTrue(provider._matchACL(user, ["*"]))

    @given(testUsers())
    def test_matchACL_person(self, user: IMSUser) -> None:
        """
        AuthProvider._matchACL matches person access with a matching user.
        """
        provider = AuthProvider(
            store=self.store(), directory=self.directory(), requireActive=False
        )

        for shortName in user.shortNames:
            self.assertTrue(provider._matchACL(user, [f"person:{shortName}"]))

    @given(testUsers())
    def test_matchACL_position(self, user: IMSUser) -> None:
        """
        AuthProvider._matchACL matches group access with a matching user.
        """
        provider = AuthProvider(
            store=self.store(), directory=self.directory(), requireActive=False
        )

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
