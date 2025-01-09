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

from collections.abc import Callable, Mapping, Sequence
from datetime import UTC
from datetime import datetime as DateTime
from datetime import timedelta as TimeDelta
from pathlib import Path
from string import ascii_letters, digits
from typing import Any, AnyStr, Optional
from unittest.mock import patch

from attrs import evolve, frozen
from hypothesis import assume, given, note
from hypothesis.strategies import (
    booleans,
    composite,
    lists,
    none,
    one_of,
    sets,
    text,
    timedeltas,
)
from twisted.web.server import Request
from twisted.web.test.test_web import DummyChannel

from ims.directory import IMSDirectory
from ims.directory.file import FileDirectory
from ims.ext.klein import HeaderName
from ims.ext.trial import TestCase
from ims.store import IMSDataStore
from ims.store.sqlite import DataStore as SQLiteDataStore

from ...directory import (
    IMSGroupID,
    IMSUser,
    IMSUserID,
    hashPassword,
    verifyPassword,
)
from .. import NotAuthorizedError
from .._exceptions import InvalidCredentialsError
from .._provider import (
    Authorization,
    AuthProvider,
    JSONWebKey,
    JSONWebToken,
    JSONWebTokenClaims,
)


__all__ = ()

from ...model import Event, FieldReport, ReportEntry


def oops(*args: Any, **kwargs: Any) -> None:  # noqa: ARG001
    raise AssertionError()


@frozen(kw_only=True)
class TestUser(IMSUser):
    """
    User for testing.
    """

    uid: IMSUserID
    shortNames: Sequence[str]
    active: bool
    groups: Sequence[IMSGroupID]
    plainTextPassword: str | None

    @property
    def hashedPassword(self) -> str | None:  # type: ignore[override]
        if self.plainTextPassword is None:
            return None
        return hashPassword(self.plainTextPassword)


@composite
def testUsers(draw: Callable[..., Any]) -> TestUser:
    return TestUser(
        uid=IMSUserID(draw(text(min_size=1))),
        shortNames=tuple(draw(lists(text(min_size=1), min_size=1))),
        active=draw(booleans()),
        groups=tuple(
            IMSGroupID(g)
            for g in draw(text(min_size=1, alphabet=ascii_letters + digits + "_"))
        ),
        plainTextPassword=draw(one_of(none(), text())),
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
            plainTextPassword=password,
        )

        self.assertEqual(user.uid, uid)
        self.assertEqual(tuple(user.shortNames), tuple(shortNames))
        self.assertEqual(user.active, active)
        self.assertEqual(tuple(user.groups), tuple(groups))
        self.assertEqual(user.plainTextPassword, password)

        if user.plainTextPassword is not None:
            self.assertIsNotNone(user.hashedPassword)
            assert user.hashedPassword is not None
            self.assertTrue(verifyPassword(user.plainTextPassword, user.hashedPassword))


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

    now = 1000000000

    def test_now_float(self) -> None:
        self.assertEqual(JSONWebTokenClaims._now(self.now), self.now)

    def test_now_none(self) -> None:
        def time() -> float:
            return self.now

        with patch("ims.auth._provider.time", time):
            JSONWebTokenClaims._now(self.now)
            self.assertEqual(JSONWebTokenClaims._now(None), self.now)

    def token(self, **kwargs: Any) -> JSONWebTokenClaims:
        defaults: dict[str, Any] = {
            "iss": "my-issuer",
            "iat": self.now - 100,
            "exp": self.now + 100,
            "sub": "some-uid",
            "preferred_username": "some-user",
            "ranger_on_site": True,
            "ranger_positions": "some-position,another-position",
        }
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
        self.assertRaises(InvalidCredentialsError, token.validateIssued, now=self.now)
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


class JSONWebTokenTests(TestCase):
    """
    Tests for :class:`JSONWebToken`
    """

    # {
    #     "iss": "my-issuer",
    #     "iat": 1000000000,
    #     "exp": 5000000000,
    #     "sub": "some-uid",
    #     "preferred_username": "some-user",
    #     "ranger_on_site": true,
    #     "ranger_positions": "some-position,another-position"
    # }
    tokenText = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJteS1pc3N1ZXIiLC"
        "JpYXQiOjEwMDAwMDAwMDAsImV4cCI6NTAwMDAwMDAwMCwic3ViIjoic29tZS11a"
        "WQiLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJzb21lLXVzZXIiLCJyYW5nZXJfb25f"
        "c2l0ZSI6dHJ1ZSwicmFuZ2VyX3Bvc2l0aW9ucyI6InNvbWUtcG9zaXRpb24sYW5"
        "vdGhlci1wb3NpdGlvbiJ9.xFkqa5ZSejA0RGmwuPtiYwjsPyjubXwKwdqhuwOiS8w"
    )
    tokenSecret = "sekret"

    def test_fromText(self) -> None:
        """
        JSONWebToken.fromText() decodes a token string correctly.
        """
        jwt = JSONWebToken.fromText(
            self.tokenText, key=JSONWebKey.fromSecret(self.tokenSecret)
        )
        claims = jwt.claims

        self.assertEqual(claims.iss, "my-issuer")
        self.assertEqual(claims.iat, 1000000000)
        self.assertEqual(claims.exp, 5000000000)
        self.assertEqual(claims.sub, "some-uid")
        self.assertEqual(claims.preferred_username, "some-user")
        self.assertEqual(claims.ranger_on_site, True)
        self.assertEqual(claims.ranger_positions, "some-position,another-position")

    def test_fromClaims(self) -> None:
        """
        JSONWebToken.fromClaims() builds a token correctly.
        """

        jwt = JSONWebToken.fromClaims(
            JSONWebTokenClaims(
                iss="my-issuer",
                iat=1000000000,
                exp=5000000000,
                sub="some-uid",
                preferred_username="some-user",
                ranger_on_site=True,
                ranger_positions="some-position,another-position",
            ),
            key=JSONWebKey.fromSecret("blah"),
        )
        claims = jwt.claims

        self.assertEqual(claims.iss, "my-issuer")
        self.assertEqual(claims.iat, 1000000000)
        self.assertEqual(claims.exp, 5000000000)
        self.assertEqual(claims.sub, "some-uid")
        self.assertEqual(claims.preferred_username, "some-user")
        self.assertEqual(claims.ranger_on_site, True)
        self.assertEqual(claims.ranger_positions, "some-position,another-position")

    def test_fromText_wrongKey(self) -> None:
        """
        JSONWebToken.fromText() raises if the key doesn't match.
        """
        self.assertRaises(
            InvalidCredentialsError,
            JSONWebToken.fromText,
            self.tokenText,
            key=JSONWebKey.fromSecret("XYZZY"),
        )

    def test_asText(self) -> None:
        """
        JSONWebToken.asText() renders the token correctly.
        """
        claims = JSONWebTokenClaims(
            iss="my-issuer",
            iat=1000000000,
            exp=5000000000,
            sub="some-uid",
            preferred_username="some-user",
            ranger_on_site=True,
            ranger_positions="some-position,another-position",
        )
        key = JSONWebKey.fromSecret(self.tokenSecret)
        jwt = JSONWebToken.fromClaims(claims, key=key)
        jwtText = jwt.asText()

        # Parse the text again so we can compare the claims
        jwtFromText = JSONWebToken.fromText(jwtText, key=key)
        self.assertEqual(jwtFromText.claims, jwt.claims)


class AuthProviderTests(TestCase):
    """
    Tests for :class:`AuthProvider`
    """

    def store(self) -> IMSDataStore:
        return SQLiteDataStore(dbPath=Path(self.mktemp()))

    def directory(self) -> IMSDirectory:
        path = Path(__file__).parent.parent.parent / "file" / "test" / "directory.yaml"
        return FileDirectory(path=path)

    @given(testUsers(), text(min_size=1))
    def test_verifyPassword_masterKey(self, user: IMSUser, masterKey: str) -> None:
        provider = AuthProvider(
            store=self.store(),
            directory=self.directory(),
            jsonWebKey=JSONWebKey.generate(),
            masterKey=masterKey,
        )

        authenticated = self.successResultOf(provider.verifyPassword(user, masterKey))
        self.assertTrue(authenticated)

    @given(testUsers())
    def test_verifyPassword_match(self, user: TestUser) -> None:
        """
        AuthProvider.verifyPassword() returns True when the user's password is
        a match.
        """
        assume(user.plainTextPassword is not None)
        assert user.plainTextPassword is not None

        provider = AuthProvider(
            store=self.store(),
            directory=self.directory(),
            jsonWebKey=JSONWebKey.generate(),
        )

        authenticated = self.successResultOf(
            provider.verifyPassword(user, user.plainTextPassword)
        )
        self.assertTrue(authenticated)

    @given(testUsers(), text())
    def test_verifyPassword_mismatch(self, user: TestUser, notPassword: str) -> None:
        """
        AuthProvider.verifyPassword() returns False when the user's password is
        not a match.
        """
        assume(user.plainTextPassword != notPassword)

        provider = AuthProvider(
            store=self.store(),
            directory=self.directory(),
            jsonWebKey=JSONWebKey.generate(),
        )

        authenticated = self.successResultOf(provider.verifyPassword(user, notPassword))
        self.assertFalse(authenticated)

    @given(testUsers(), text())
    def test_verifyPassword_none(self, user: IMSUser, password: str) -> None:
        """
        AuthProvider.verifyPassword() returns False when the user's password is
        None.
        """
        user = evolve(user, plainTextPassword=None)  # type: ignore[misc]
        provider = AuthProvider(
            store=self.store(),
            directory=self.directory(),
            jsonWebKey=JSONWebKey.generate(),
        )

        authenticated = self.successResultOf(provider.verifyPassword(user, password))
        self.assertFalse(authenticated)

    @given(
        testUsers(),
        timedeltas(min_value=TimeDelta(minutes=10), max_value=TimeDelta(days=1000)),
    )
    def test_credentialsForUser(self, user: IMSUser, duration: TimeDelta) -> None:
        """
        AuthProvider.credentialsForUser generates a valid token for the user.
        """
        jsonWebKey = JSONWebKey.generate()
        provider = AuthProvider(
            store=self.store(),
            directory=self.directory(),
            jsonWebKey=jsonWebKey,
        )

        now = DateTime.now(tz=UTC)

        def approximateTimestamps(a: float, b: float) -> bool:
            fuzz = 1.5
            return b < a + fuzz and b > a - fuzz

        credentials = self.successResultOf(provider.credentialsForUser(user, duration))
        tokenText = credentials.get("token")
        token = JSONWebToken.fromText(tokenText, key=jsonWebKey)
        claims = token.claims

        self.assertEqual(claims.iss, AuthProvider._jwtIssuer)
        self.assertTrue(approximateTimestamps(claims.iat, now.timestamp()))
        self.assertTrue(approximateTimestamps(claims.exp, (now + duration).timestamp()))
        self.assertEqual(claims.sub, user.uid)
        self.assertEqual(claims.preferred_username, user.shortNames[0])
        self.assertEqual(claims.ranger_on_site, user.active)
        self.assertEqual(claims.ranger_positions, ",".join(user.groups))

    @given(
        testUsers(),
        timedeltas(min_value=TimeDelta(minutes=10), max_value=TimeDelta(days=1000)),
    )
    def test_userFromBearerAuthorization(
        self, user: IMSUser, duration: TimeDelta
    ) -> None:
        """
        AuthProvider._userFromBearerAuthorization converts a bearer token from
        an HTTP authorization header into a user.
        """
        provider = AuthProvider(
            store=self.store(),
            directory=self.directory(),
            jsonWebKey=JSONWebKey.generate(),
        )
        token = provider._tokenForUser(user, duration).asText()
        userFromToken = provider._userFromBearerAuthorization(f"Bearer {token}")

        note(f"user={user}")
        note(f"user={userFromToken}")

        self.assertIsNotNone(userFromToken)
        assert userFromToken is not None  # for mypy

        self.assertEqual(userFromToken.uid, user.uid)
        # Only the first shortName is kept
        self.assertEqual(userFromToken.shortNames, (user.shortNames[0],))
        self.assertEqual(userFromToken.active, user.active)
        self.assertEqual(userFromToken.groups, user.groups)
        self.assertEqual(userFromToken.hashedPassword, None)

    def test_authenticateRequest(self) -> None:
        raise NotImplementedError()

    test_authenticateRequest.todo = (  # type: ignore[attr-defined]
        "unimplemented"
    )

    def test_jsonWebKey(self) -> None:
        """
        AuthProvider._jsonWebKey generates a JWT secret.
        """
        provider = AuthProvider(
            store=self.store(),
            directory=self.directory(),
            jsonWebKey=JSONWebKey.generate(),
        )

        self.assertIsInstance(provider._jsonWebKey, JSONWebKey)

    def test_jsonWebKey_same(self) -> None:
        """
        AuthProvider._jsonWebKey is the same secret.
        """
        provider = AuthProvider(
            store=self.store(),
            directory=self.directory(),
            jsonWebKey=JSONWebKey.generate(),
        )

        self.assertIdentical(provider._jsonWebKey, provider._jsonWebKey)

    def test_matchACL_none_noUser(self) -> None:
        """
        AuthProvider._matchACL does not match no access with None user.
        """
        provider = AuthProvider(
            store=self.store(),
            directory=self.directory(),
            jsonWebKey=JSONWebKey.generate(),
        )

        self.assertFalse(provider._matchACL(None, []))

    @given(testUsers())
    def test_matchACL_none_user(self, user: IMSUser) -> None:
        """
        AuthProvider._matchACL does not match no access with a user.
        """
        provider = AuthProvider(
            store=self.store(),
            directory=self.directory(),
            jsonWebKey=JSONWebKey.generate(),
        )

        self.assertFalse(provider._matchACL(user, []))

    def test_matchACL_public_noUser(self) -> None:
        """
        AuthProvider._matchACL matches public ("**") access with None user.
        """
        provider = AuthProvider(
            store=self.store(),
            directory=self.directory(),
            jsonWebKey=JSONWebKey.generate(),
        )

        self.assertTrue(provider._matchACL(None, ["**"]))

    @given(testUsers())
    def test_matchACL_public_user(self, user: IMSUser) -> None:
        """
        AuthProvider._matchACL matches public ("**") access with a user.
        """
        provider = AuthProvider(
            store=self.store(),
            directory=self.directory(),
            jsonWebKey=JSONWebKey.generate(),
        )

        self.assertTrue(provider._matchACL(user, ["**"]))

    def test_matchACL_any_noUser(self) -> None:
        """
        AuthProvider._matchACL does not match any ("*") access with None user.
        """
        provider = AuthProvider(
            store=self.store(),
            directory=self.directory(),
            jsonWebKey=JSONWebKey.generate(),
            requireActive=False,
        )

        self.assertFalse(provider._matchACL(None, ["*"]))

    @given(testUsers())
    def test_matchACL_any_user(self, user: IMSUser) -> None:
        """
        AuthProvider._matchACL matches any ("*") access with a user.
        """
        provider = AuthProvider(
            store=self.store(),
            directory=self.directory(),
            jsonWebKey=JSONWebKey.generate(),
            requireActive=False,
        )

        self.assertTrue(provider._matchACL(user, ["*"]))

    @given(testUsers())
    def test_matchACL_person(self, user: IMSUser) -> None:
        """
        AuthProvider._matchACL matches person access with a matching user.
        """
        provider = AuthProvider(
            store=self.store(),
            directory=self.directory(),
            jsonWebKey=JSONWebKey.generate(),
            requireActive=False,
        )

        for shortName in user.shortNames:
            self.assertTrue(provider._matchACL(user, [f"person:{shortName}"]))

    @given(testUsers())
    def test_matchACL_position(self, user: IMSUser) -> None:
        """
        AuthProvider._matchACL matches group access with a matching user.
        """
        provider = AuthProvider(
            store=self.store(),
            directory=self.directory(),
            jsonWebKey=JSONWebKey.generate(),
            requireActive=False,
        )

        for groupID in user.groups:
            self.assertTrue(provider._matchACL(user, [f"position:{groupID}"]))

    def test_authorizationsForUser(self) -> None:
        raise NotImplementedError()

    test_authorizationsForUser.todo = (  # type: ignore[attr-defined]
        "unimplemented"
    )

    def test_authorizeRequest(self) -> None:
        # Set up DB and AuthProvider with a single user
        store = self.store()
        provider = AuthProvider(
            store=store,
            directory=self.directory(),
            jsonWebKey=JSONWebKey.generate(),
            requireActive=False,
        )
        self.successResultOf(store.upgradeSchema())
        event = "2024"
        self.successResultOf(store.createEvent(Event(id=event)))
        user = TestUser(
            uid=IMSUserID("my-id"),
            shortNames=("Slumber",),
            active=True,
            groups=(),
            plainTextPassword="some-password",
        )
        personUser = f"person:{user.shortNames[0]}"
        token = provider._tokenForUser(user, TimeDelta(days=1)).asText()
        request = MockReq(
            user,
            {HeaderName.authorization.value: f"Bearer {token}"},
        )

        # Stage 1: the user and the user's group have no permissions
        self.failureResultOf(
            provider.authorizeRequest(
                request=request,
                eventID=event,
                requiredAuthorizations=Authorization.readIncidents,
            ),
            NotAuthorizedError,
        )
        self.assertEqual(request.authorizations, Authorization.none)

        # Stage 2: the user is now a reporter
        self.successResultOf(store.setReporters(event, (personUser,)))
        # Now the user is able to writeFieldReports, but that's it
        self.successResultOf(
            provider.authorizeRequest(
                request=request,
                eventID=event,
                requiredAuthorizations=Authorization.writeFieldReports,
            )
        )
        self.assertEqual(request.authorizations, Authorization.writeFieldReports)
        self.failureResultOf(
            provider.authorizeRequest(
                request=request,
                eventID=event,
                requiredAuthorizations=Authorization.readIncidents,
            ),
            NotAuthorizedError,
        )

        # Stage 3: the user can read incidents
        self.successResultOf(store.setReporters(event, ()))
        self.successResultOf(store.setReaders(event, (personUser,)))
        self.successResultOf(
            provider.authorizeRequest(
                request=request,
                eventID=event,
                requiredAuthorizations=Authorization.readIncidents,
            ),
        )
        self.assertEqual(
            request.authorizations,
            Authorization.readPersonnel | Authorization.readIncidents,
        )

        # Stage 4: the user can write incidents
        self.successResultOf(store.setReaders(event, ()))
        self.successResultOf(store.setWriters(event, (personUser,)))
        self.successResultOf(
            provider.authorizeRequest(
                request=request,
                eventID=event,
                requiredAuthorizations=Authorization.writeIncidents,
            ),
        )
        self.assertEqual(
            request.authorizations,
            Authorization.readPersonnel
            | Authorization.readIncidents
            | Authorization.writeIncidents
            | Authorization.writeFieldReports,
        )

        # Stage 5: no event is provided in the request
        self.failureResultOf(
            provider.authorizeRequest(
                request=request,
                eventID=None,
                requiredAuthorizations=Authorization.writeIncidents,
            ),
            NotAuthorizedError,
        )
        self.assertEqual(request.authorizations, Authorization.none)

    def test_authorizeReqForFieldReport(self) -> None:
        # Set up DB and AuthProvider with a single user
        store = self.store()
        provider = AuthProvider(
            store=store,
            directory=self.directory(),
            jsonWebKey=JSONWebKey.generate(),
            requireActive=False,
        )
        self.successResultOf(store.upgradeSchema())
        event = "2024"
        self.successResultOf(store.createEvent(Event(id=event)))
        user = TestUser(
            uid=IMSUserID("my-id"),
            shortNames=("Slumber",),
            active=True,
            groups=(),
            plainTextPassword="some-password",
        )
        personUser = f"person:{user.shortNames[0]}"
        token = provider._tokenForUser(user, TimeDelta(days=1)).asText()
        request = MockReq(
            user,
            {HeaderName.authorization.value: f"Bearer {token}"},
        )

        # This FieldReport includes an entry by the user in session
        reportByUser = FieldReport(
            eventID=event,
            number=0,
            created=DateTime.now(tz=UTC),
            summary=None,
            incidentNumber=0,
            reportEntries=(
                ReportEntry(
                    id=0,
                    created=DateTime.now(tz=UTC),
                    author="SomeoneElse",
                    automatic=False,
                    text="abc",
                    stricken=False,
                ),
                ReportEntry(
                    id=1,
                    created=DateTime.now(tz=UTC),
                    author="Slumber",
                    automatic=False,
                    text="abcde",
                    stricken=False,
                ),
            ),
        )
        # This report doesn't include an entry by the user in session
        reportNotByUser = FieldReport(
            eventID=event,
            number=1,
            created=DateTime.now(tz=UTC),
            summary=None,
            incidentNumber=1,
            reportEntries=(),
        )

        # Stage 1: user doesn't have writeFieldReports, so no incident
        # report can be read.
        self.failureResultOf(
            provider.authorizeRequestForFieldReport(
                request=request,
                fieldReport=reportByUser,
            ),
            NotAuthorizedError,
        )
        self.assertEqual(request.authorizations, Authorization.none)

        # Stage 2: user is a reporter
        self.successResultOf(store.setReporters(event, (personUser,)))
        self.successResultOf(
            provider.authorizeRequestForFieldReport(
                request=request,
                fieldReport=reportByUser,
            ),
        )
        self.assertEqual(request.authorizations, Authorization.writeFieldReports)
        self.failureResultOf(
            provider.authorizeRequestForFieldReport(
                request=request,
                fieldReport=reportNotByUser,
            ),
            NotAuthorizedError,
        )
        self.assertEqual(request.authorizations, Authorization.writeFieldReports)

        # Stage 3: user is a reader
        self.successResultOf(store.setReporters(event, ()))
        self.successResultOf(store.setReaders(event, (personUser,)))
        self.successResultOf(
            provider.authorizeRequestForFieldReport(
                request=request,
                fieldReport=reportByUser,
            ),
        )
        self.successResultOf(
            provider.authorizeRequestForFieldReport(
                request=request,
                fieldReport=reportNotByUser,
            ),
        )
        self.assertEqual(
            request.authorizations,
            Authorization.readPersonnel | Authorization.readIncidents,
        )

        # Stage 4: user is a writer
        self.successResultOf(store.setReaders(event, ()))
        self.successResultOf(store.setWriters(event, (personUser,)))
        self.successResultOf(
            provider.authorizeRequestForFieldReport(
                request=request,
                fieldReport=reportNotByUser,
            ),
        )
        self.assertEqual(
            request.authorizations,
            Authorization.readPersonnel
            | Authorization.readIncidents
            | Authorization.writeIncidents
            | Authorization.writeFieldReports,
        )


class MockReq(Request):
    def __init__(self, user: Optional[TestUser], headers: Mapping[str, str]) -> None:
        super().__init__(DummyChannel(), False)
        self.user = user  # type: ignore[assignment]
        self.headers = headers
        self.authorizations = Authorization.none

    def getHeader(self, key: AnyStr) -> Optional[AnyStr]:
        return self.headers.get(str(key))  # type: ignore[return-value]
