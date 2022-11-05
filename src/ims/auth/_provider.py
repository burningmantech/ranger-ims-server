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
Incident Management System web application authentication provider.
"""

from collections.abc import Container, Mapping
from datetime import datetime as DateTime
from datetime import timedelta as TimeDelta
from enum import Flag, auto
from typing import Any, ClassVar

from attrs import field, frozen, mutable
from jwcrypto.jwk import JWK
from jwcrypto.jwt import JWT
from twisted.logger import Logger
from twisted.web.iweb import IRequest

from ims.directory import IMSDirectory, IMSUser, RangerUser
from ims.model import IncidentReport
from ims.store import IMSDataStore

from ._exceptions import NotAuthenticatedError, NotAuthorizedError


__all__ = ()


class Authorization(Flag):
    """
    Authorizations
    """

    none = 0

    imsAdmin = auto()

    readPersonnel = auto()

    readIncidents = auto()
    writeIncidents = auto()

    writeIncidentReports = auto()

    all = (
        imsAdmin
        | readPersonnel
        | readIncidents
        | writeIncidents
        | writeIncidentReports
    )


@frozen(kw_only=True)
class AuthProvider:
    """
    Provider for authentication and authorization support.
    """

    _log: ClassVar[Logger] = Logger()
    _jwtIssuer: ClassVar[str] = "ranger-ims-server"

    @mutable(kw_only=True, eq=False)
    class _State:
        """
        Internal mutable state for :class:`RangerDirectory`.
        """

        jwtSecret: object | None = None

    store: IMSDataStore
    directory: IMSDirectory

    requireActive: bool = True
    adminUsers: frozenset[str] = frozenset()
    masterKey: str = ""

    _state: _State = field(factory=_State)

    async def verifyPassword(self, user: IMSUser, password: str) -> bool:
        """
        Verify a password for the given user.
        """
        if self.masterKey and password == self.masterKey:
            return True

        try:
            authenticated = await user.verifyPassword(password)
        except Exception as e:
            self._log.critical(
                "Unable to check password for user {user}: {error}",
                user=user,
                error=e,
            )
            authenticated = False

        self._log.debug(
            "Valid credentials for {user}: {result}",
            user=user,
            result=authenticated,
        )

        return authenticated

    @property
    def _jwtSecret(self) -> object:
        if self._state.jwtSecret is None:
            self._log.info("Generating JWT secret")
            self._state.jwtSecret = JWK.generate(kty="oct", size=256)
        return self._state.jwtSecret

    async def credentialsForUser(
        self, user: IMSUser, duration: TimeDelta
    ) -> Mapping[str, Any]:
        """
        Generate a JWT token for the given user.
        """
        now = DateTime.now()
        expiration = now + duration

        token = JWT(
            header=dict(typ="JWT", alg="HS256"),
            claims=dict(
                iss=self._jwtIssuer,  # Issuer
                sub=user.uid,  # Subject
                # aud=None, # Audience
                exp=int(expiration.timestamp()),  # Expiration
                # nbf=None,  # Not before
                iat=int(now.timestamp()),  # Issued at
                # jti=None,  # JWT ID
                preferred_username=user.shortNames[0],
            ),
        )
        token.make_signed_token(self._jwtSecret)
        return dict(token=token.serialize())

    def authenticateRequest(
        self, request: IRequest, optional: bool = False
    ) -> None:
        """
        Authenticate a request.

        @param request: The request to authenticate.

        @param optional: If true, do not raise NotAuthenticatedError() if no
            user is associated with the request.
        """
        session = request.getSession()
        user = getattr(session, "user", None)
        request.user = user  # type: ignore[attr-defined]

        if user is None and not optional:
            self._log.debug("Authentication failed")
            raise NotAuthenticatedError("No user logged in")

    def _matchACL(self, user: IMSUser | None, acl: Container[str]) -> bool:
        """
        Match a user against a set of ACLs associated with an event's readers,
        writers and reporters.

        An ACL of "**" will always match, even for the None user.

        If the requireActive of this instance is True, all other ACLs will never
        match a user if the user is not active.

        An ACL of "*" matches all users other than the None user.

        An ACL of the form "person:{user}" will match a user of one of the
        user's short names equals {user}.

        An ACL of the form "position:{group}" will match a user if the ID of
        one of the groups that the user is a member of equals {group}.
        """
        if "**" in acl:
            return True

        if user is not None:
            if self.requireActive and not user.active:
                return False

            if "*" in acl:
                return True

            for shortName in user.shortNames:
                if ("person:" + shortName) in acl:
                    return True

            for group in user.groups:
                if ("position:" + group) in acl:
                    return True

        return False

    async def authorizationsForUser(
        self, user: IMSUser | None, eventID: str | None
    ) -> Authorization:
        """
        Look up the authorizations that a user has for a given event.
        """
        authorizations = Authorization.none

        if user is not None:
            authorizations |= Authorization.readPersonnel

            for shortName in user.shortNames:
                if shortName in self.adminUsers:
                    authorizations |= Authorization.imsAdmin

        if eventID is not None:
            if self._matchACL(
                user, frozenset(await self.store.writers(eventID))
            ):
                authorizations |= Authorization.writeIncidents
                authorizations |= Authorization.readIncidents
                authorizations |= Authorization.writeIncidentReports

            else:
                if self._matchACL(
                    user, frozenset(await self.store.readers(eventID))
                ):
                    authorizations |= Authorization.readIncidents

                if self._matchACL(
                    user,
                    frozenset(await self.store.reporters(eventID)),
                ):
                    authorizations |= Authorization.writeIncidentReports

        self._log.debug(
            "Authz for {user}: {authorizations}",
            user=user,
            authorizations=authorizations,
        )

        return authorizations

    async def authorizeRequest(
        self,
        request: IRequest,
        eventID: str | None,
        requiredAuthorizations: Authorization,
    ) -> None:
        """
        Determine whether the user attached to a request has the required
        authorizations in the context of a given event.
        """
        self.authenticateRequest(request)

        userAuthorizations = await self.authorizationsForUser(
            request.user, eventID  # type: ignore[attr-defined]
        )
        request.authorizations = (  # type: ignore[attr-defined]
            userAuthorizations
        )

        if not (requiredAuthorizations & userAuthorizations):
            self._log.debug(
                "Authorization failed for {request.user}. "
                "Requires {requiredAuthorizations}, has {userAuthorizations}. "
                "URI: {request.uri}",
                request=request,
                requiredAuthorizations=requiredAuthorizations,
                userAuthorizations=userAuthorizations,
            )
            raise NotAuthorizedError("User not authorized")

    async def authorizeRequestForIncidentReport(
        self, request: IRequest, incidentReport: IncidentReport
    ) -> None:
        """
        Determine whether the user attached to a request has the required
        authorizations to read the incident report with the given number.
        """
        # The author of the incident report should be allowed to read and write
        # to it.

        user: RangerUser = request.user  # type: ignore[attr-defined]

        if user is not None and incidentReport.reportEntries:
            rangerHandle = user.ranger.handle
            for reportEntry in incidentReport.reportEntries:
                if reportEntry.author == rangerHandle:
                    request.authorizations = (  # type: ignore[attr-defined]
                        Authorization.writeIncidentReports
                    )
                    return

        # Otherwise, use the ACL for the event associated with the incident
        # report.

        await self.authorizeRequest(
            request, incidentReport.eventID, Authorization.readIncidents
        )
