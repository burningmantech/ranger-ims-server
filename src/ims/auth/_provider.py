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

from datetime import datetime as DateTime, timedelta as TimeDelta
from enum import Flag, auto
from typing import Any, ClassVar, Container, FrozenSet, Mapping, Optional

from attr import Factory, attrs

from jwcrypto.jwk import JWK
from jwcrypto.jwt import JWT

from twisted.logger import Logger
from twisted.web.iweb import IRequest

from ims.directory import IMSUser
from ims.model import Event, IncidentReport
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


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class AuthProvider:
    """
    Provider for authentication and authorization support.
    """

    _log: ClassVar[Logger] = Logger()

    @attrs(frozen=False, auto_attribs=True, kw_only=True, eq=False)
    class _State:
        """
        Internal mutable state for :class:`RangerDirectory`.
        """

        jwtSecret: Optional[object] = None

    store: IMSDataStore

    requireActive: bool = True
    adminUsers: FrozenSet[str] = frozenset()
    masterKey: str = ""

    _state: _State = Factory(_State)

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
            key = JWK.generate(kty="oct", size=256)
            self._log.info(
                "Generated JWT secret: {secret}", secret=key.export()
            )
            self._state.jwtSecret = key
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
                iss="ranger-ims-server",  # Issuer
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
        return dict(
            token=token.serialize(),
            person_id=user.uid,
            username=user.shortNames[0],
            expires_in=None,
        )

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
        request.user = getattr(session, "user", None)

        if request.user is None and not optional:
            self._log.debug("Authentication failed")
            raise NotAuthenticatedError("No user logged in")

    async def authorizationsForUser(
        self, user: IMSUser, event: Optional[Event]
    ) -> Authorization:
        """
        Look up the authorizations that a user has for a given event.
        """

        def matchACL(user: IMSUser, acl: Container[str]) -> bool:
            if "**" in acl:
                return True

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

        authorizations = Authorization.none

        if user is not None:
            authorizations |= Authorization.readPersonnel

            for shortName in user.shortNames:
                if shortName in self.adminUsers:
                    authorizations |= Authorization.imsAdmin

                if event is not None:
                    if matchACL(
                        user, frozenset(await self.store.writers(event))
                    ):
                        authorizations |= Authorization.writeIncidents
                        authorizations |= Authorization.readIncidents
                        authorizations |= Authorization.writeIncidentReports

                    else:
                        if matchACL(
                            user, frozenset(await self.store.readers(event))
                        ):
                            authorizations |= Authorization.readIncidents

                        if matchACL(
                            user, frozenset(await self.store.reporters(event))
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
        event: Optional[Event],
        requiredAuthorizations: Authorization,
    ) -> None:
        """
        Determine whether the user attached to a request has the required
        authorizations in the context of a given event.
        """
        self.authenticateRequest(request)

        userAuthorizations = await self.authorizationsForUser(
            request.user, event
        )
        request.authorizations = userAuthorizations

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

        if request.user is not None and incidentReport.reportEntries:
            rangerHandle = request.user.rangerHandle
            for reportEntry in incidentReport.reportEntries:
                if reportEntry.author == rangerHandle:
                    request.authorizations = Authorization.writeIncidentReports
                    return

        # Otherwise, use the ACL for the event associated with the incident
        # report.

        await self.authorizeRequest(
            request, incidentReport.event, Authorization.readIncidents
        )
