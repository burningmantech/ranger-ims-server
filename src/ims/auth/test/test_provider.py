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

from pathlib import Path
from typing import Any, Callable, Optional, Sequence, cast

from attr import attrs, evolve
from hypothesis import assume, given
from hypothesis.strategies import booleans, composite, lists, none, one_of, text

from ims.ext.trial import TestCase
from ims.model import Event, Ranger, RangerStatus
from ims.store import IMSDataStore
from ims.store.sqlite import DataStore as SQLiteDataStore

from ...directory import IMSGroupID, IMSUser, IMSUserID, RangerUser
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
    _password: Optional[str]

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
        return SQLiteDataStore(dbPath=Path(self.mktemp()))

    @given(
        testUsers(),
        text(min_size=1),
    )
    def test_verifyPassword_masterKey(
        self, user: TestUser, masterKey: str
    ) -> None:
        """
        AuthProvider.verifyPassword() returns True when the master key is used
        as the password.
        """
        provider = AuthProvider(store=self.store(), masterKey=masterKey)

        authorization = self.successResultOf(
            provider.verifyPassword(user, masterKey)
        )
        self.assertTrue(authorization)

    @given(testUsers())
    def test_verifyPassword_match(self, user: TestUser) -> None:
        """
        AuthProvider.verifyPassword() returns True when the user's password is
        a match.
        """
        assume(user._password is not None)
        assert user._password is not None

        provider = AuthProvider(store=self.store())

        authorization = self.successResultOf(
            provider.verifyPassword(user, user._password)
        )
        self.assertTrue(authorization)

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

        authorization = self.successResultOf(
            provider.verifyPassword(user, notPassword)
        )
        self.assertFalse(authorization)

    @given(testUsers(), text())
    def test_verifyPassword_none(self, user: TestUser, password: str) -> None:
        """
        AuthProvider.verifyPassword() returns False when the user's password is
        None.
        """
        user = evolve(user, password=None)
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

    async def storeWithEvent(self, event: Event) -> IMSDataStore:
        store = self.store()
        self.successResultOf(store.upgradeSchema())
        self.successResultOf(store.createEvent(event))
        return store

    def userWithRangerHandle(self, handle: str, *, active: bool) -> IMSUser:
        return RangerUser(
            ranger=Ranger(
                handle=handle,
                name="Pail Container",
                status=RangerStatus.active,
                email=[],
                enabled=active,
                directoryID=None,
                password=None,
            ),
            groups=[],
        )

    def authorizationsForUser(
        self,
        user: Optional[IMSUser],
        admin: bool = False,
        reader: bool = False,
        reporter: bool = False,
        writer: bool = False,
    ) -> Authorization:
        if admin:
            assert user is not None
            adminUsers = frozenset([user.uid])
        else:
            adminUsers = frozenset()

        event = Event(id="Event")
        store = self.successResultOf(self.storeWithEvent(event))
        provider = AuthProvider(store=store, adminUsers=adminUsers)

        if reader:
            assert user is not None
            self.successResultOf(
                store.setReaders(event.id, (f"person:{user.shortNames[0]}",))
            )

        if reporter:
            assert user is not None
            self.successResultOf(
                store.setReporters(event.id, (f"person:{user.shortNames[0]}",))
            )

        if writer:
            assert user is not None
            self.successResultOf(
                store.setWriters(event.id, (f"person:{user.shortNames[0]}",))
            )

        return cast(
            Authorization,
            self.successResultOf(
                provider.authorizationsForUser(user, event.id)
            ),
        )

    def test_authorization_default_noneUser(self) -> None:
        """
        None user is not authorized for anything by default.
        """
        authorizations = self.authorizationsForUser(None)
        self.assertEqual(authorizations, Authorization.none)

    def test_authorization_default_user(self) -> None:
        """
        Users by default get readPersonnel only.
        """
        for active in (True, False):
            user = self.userWithRangerHandle("Bucket", active=active)
            authorizations = self.authorizationsForUser(user)

            self.assertFalse(authorizations & Authorization.imsAdmin)
            self.assertTrue(authorizations & Authorization.readPersonnel)
            self.assertFalse(authorizations & Authorization.readIncidents)
            self.assertFalse(authorizations & Authorization.writeIncidents)
            self.assertFalse(
                authorizations & Authorization.writeIncidentReports
            )

    def test_authorization_admin_not(self) -> None:
        """
        User not in admin list is not an admin.
        """
        for active in (True, False):
            user = self.userWithRangerHandle("Bucket", active=active)
            authorizations = self.authorizationsForUser(user)

            self.assertFalse(authorizations & Authorization.imsAdmin)

    def test_authorization_admin(self) -> None:
        """
        User in admin list is an admin.
        """
        for active in (True, False):
            user = self.userWithRangerHandle("Bucket", active=active)
            authorizations = self.authorizationsForUser(user, admin=True)

            self.assertTrue(authorizations & Authorization.imsAdmin)

    def test_authorization_reader(self) -> None:
        """
        User has readIncidents if reader and is active, otherwise defaults.
        """
        for active in (True, False):
            user = self.userWithRangerHandle("Bucket", active=active)
            authorizations = self.authorizationsForUser(user, reader=True)
            assertIfActive = self.assertTrue if active else self.assertFalse

            self.assertFalse(authorizations & Authorization.imsAdmin)
            self.assertTrue(authorizations & Authorization.readPersonnel)
            assertIfActive(authorizations & Authorization.readIncidents)
            self.assertFalse(authorizations & Authorization.writeIncidents)
            self.assertFalse(
                authorizations & Authorization.writeIncidentReports
            )

    def test_authorization_reporter(self) -> None:
        """
        User has writeIncidentReports if reporter and is active, otherwise
        defaults.
        """
        for active in (True, False):
            user = self.userWithRangerHandle("Bucket", active=active)
            authorizations = self.authorizationsForUser(user, reporter=True)
            assertIfActive = self.assertTrue if active else self.assertFalse

            self.assertFalse(authorizations & Authorization.imsAdmin)
            self.assertTrue(authorizations & Authorization.readPersonnel)
            self.assertFalse(authorizations & Authorization.readIncidents)
            self.assertFalse(authorizations & Authorization.writeIncidents)
            assertIfActive(authorizations & Authorization.writeIncidentReports)

    def test_authorization_writer(self) -> None:
        """
        User has writeIncidents, readIncidents, and writeIncidentReports if
        writer and is active, otherwise defaults.
        """
        for active in (True, False):
            user = self.userWithRangerHandle("Bucket", active=active)
            authorizations = self.authorizationsForUser(user, writer=True)
            assertIfActive = self.assertTrue if active else self.assertFalse

            self.assertFalse(authorizations & Authorization.imsAdmin)
            self.assertTrue(authorizations & Authorization.readPersonnel)
            assertIfActive(authorizations & Authorization.readIncidents)
            assertIfActive(authorizations & Authorization.writeIncidents)
            assertIfActive(authorizations & Authorization.writeIncidentReports)

    def test_authorizeRequest(self) -> None:
        raise NotImplementedError()

    test_authorizeRequest.todo = "unimplemented"  # type: ignore[attr-defined]

    def test_authorizeReqForIncidentReport(self) -> None:
        raise NotImplementedError()

    test_authorizeReqForIncidentReport.todo = (  # type: ignore[attr-defined]
        "unimplemented"
    )
