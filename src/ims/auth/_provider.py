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
from time import time
from typing import Any, ClassVar

from attrs import field, frozen, mutable
from attrs.validators import instance_of
from cattrs.preconf.json import make_converter as makeJSONConverter
from jwcrypto.jwk import JWK
from jwcrypto.jws import InvalidJWSSignature
from jwcrypto.jwt import JWT
from twisted.logger import Logger
from twisted.web.iweb import IRequest

from ims.directory import IMSDirectory, IMSGroupID, IMSUser, IMSUserID
from ims.ext.klein import HeaderName
from ims.model import IncidentReport
from ims.store import IMSDataStore

from ._exceptions import (
    InvalidCredentialsError,
    NotAuthenticatedError,
    NotAuthorizedError,
)


__all__ = ()


jsonConverter = makeJSONConverter()


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
class JSONWebTokenClaims:
    """
    Claims made by a JSON web token.
    """

    @staticmethod
    def _now(now: float | None) -> float:
        if now is None:
            return time()
        else:
            return now

    # issuer
    iss: str = field(validator=instance_of(str))
    # issued timestamp
    iat: float = field(validator=instance_of((int, float)))
    # expiration timestamp
    exp: float = field(validator=instance_of((int, float)))
    # subject
    sub: str = field(validator=instance_of(str))
    # preferred username
    preferred_username: str = field(validator=instance_of(str))
    # on site (actively working)
    ranger_on_site: bool = field(validator=instance_of(bool))
    # positions
    ranger_positions: str = field(validator=instance_of(str))

    def validateIssuer(self, issuer: str) -> None:
        """
        Validate claim's issuer against an expected issuer.

        @raise InvalidCredentialsError: if the issuer is incorrect.
        """
        if self.iss != issuer:
            raise InvalidCredentialsError(
                f"JWT token was issued by {self.iss}, not {issuer}"
            )

    def validateIssued(self, now: float | None = None) -> None:
        """
        Validate claim's issued time against the current time.

        @raise InvalidCredentialsError: if the issued time is not valid.
        """
        now = self._now(now)

        if self.iat > now:
            raise InvalidCredentialsError("JWT token was issued in the future")

    def validateExpiration(self, now: float | None = None) -> None:
        """
        Validate claim's expiration time against the current time.

        @raise InvalidCredentialsError: if the expiration time is not valid.
        """
        now = self._now(now)

        if self.exp < now:
            raise InvalidCredentialsError("JWT token is expired")

    def validate(
        self, *, issuer: str | None = None, now: float | None = None
    ) -> None:
        """
        Validate claim.

        @raise InvalidCredentialsError: if the claim is not valid.
        """
        now = self._now(now)

        if issuer is not None:
            self.validateIssuer(issuer)

        self.validateIssued(now)
        self.validateExpiration(now)


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
            authenticated = user.verifyPassword(password)
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
                ranger_on_site=user.active,
                ranger_positions=",".join(user.groups),
            ),
        )
        token.make_signed_token(self._jwtSecret)
        return dict(token=token.serialize())

    def _userFromBearerAuthorization(
        self, authorization: str | None
    ) -> IMSUser | None:
        """
        Given an Authorization header value with a bearer token, create an
        IMSUser.

        @raises InvalidCredentialsError: if the token is invalid.
        """
        if not authorization:
            return None

        token = authorization.removeprefix("Bearer ")

        if token is authorization:  # Prefix doesn't match
            return None

        try:
            jwt = JWT(jwt=token, key=self._jwtSecret)
        except InvalidJWSSignature as e:
            self._log.info(
                "Invalid JWT signature in authorization header", error=e
            )
            raise InvalidCredentialsError("Invalid JWT token") from e
        else:
            claims = jsonConverter.loads(jwt.claims, JSONWebTokenClaims)
            claims.validate(issuer=self._jwtIssuer)
            self._log.debug(
                "Valid JWT token for subject {subject}", subject=claims.sub
            )

            return IMSUser(
                uid=IMSUserID(claims.sub),
                shortNames=(claims.preferred_username,),
                active=claims.ranger_on_site,
                groups=tuple(
                    IMSGroupID(gid)
                    for gid in claims.ranger_positions.split(",")
                ),
            )

    def checkAuthentication(self, request: IRequest) -> None:
        """
        Check whether the request has previously been authenticated, and if so,
        set request.user.
        """
        if getattr(request, "user", None) is None:
            authorization = request.getHeader(HeaderName.authorization.value)
            user = self._userFromBearerAuthorization(authorization)

            if user is None:
                session = request.getSession()
                user = getattr(session, "user", None)

            request.user = user  # type: ignore[attr-defined]

    def authenticateRequest(self, request: IRequest) -> None:
        """
        Authenticate a request's user.

        @param request: The request to authenticate.

        @raises NotAuthenticatedError: If no user is authenticated.
        """
        self.checkAuthentication(request)

        if getattr(request, "user", None) is None:
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

        user: IMSUser = request.user  # type: ignore[attr-defined]

        if user is not None and incidentReport.reportEntries:
            rangerHandle = user.shortNames[0]
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
