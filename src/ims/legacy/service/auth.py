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
Incident Management System authorization and authentication.
"""

from hashlib import sha1
from typing import Container, Optional, Sequence

from attr import attrib, attrs
from attr.validators import instance_of

from twisted.logger import Logger
from twisted.python.constants import FlagConstant, Flags
from twisted.python.url import URL
from twisted.web.iweb import IRequest

from ims.ext.klein import KleinRenderable
from ims.model import Event, Ranger

from .error import NotAuthenticatedError, NotAuthorizedError
from .klein import route
from .urls import URLs
from ..element.login import LoginPage


__all__ = (
    "Authorization",
    "AuthMixIn",
)



class Authorization(Flags):
    """
    Authorizations
    """

    imsAdmin = FlagConstant()

    readPersonnel = FlagConstant()

    readIncidents  = FlagConstant()
    writeIncidents = FlagConstant()

    readIncidentReports  = FlagConstant()
    writeIncidentReports = FlagConstant()


Authorization.none = Authorization.imsAdmin ^ Authorization.imsAdmin
Authorization.all = (
    Authorization.imsAdmin             |
    Authorization.readPersonnel        |
    Authorization.readIncidents        |
    Authorization.writeIncidents       |
    Authorization.readIncidentReports  |
    Authorization.writeIncidentReports
)



@attrs(frozen=True)
class User(object):
    """
    Application user.
    """

    _log = Logger()


    ranger = attrib(validator=instance_of(Ranger))  # type: Ranger


    @property
    def shortNames(self) -> Sequence[str]:
        return (self.ranger.handle,)


    def verifyPlaintextPassword(self, password: str) -> bool:
        hashedPassword = self.ranger.password

        if hashedPassword is None:
            return False

        # Reference Clubhouse code: standard/controllers/security.php#L457
        try:
            # DMS password field is a salt and a SHA-1 hash (hex digest),
            # separated by ":".
            salt, hashValue = hashedPassword.split(":")
        except ValueError:
            # Invalid password format, punt
            self._log.error("Invalid DMS password for user {user}", user=self)
            return False

        hashed = sha1((salt + password).encode("utf-8")).hexdigest()

        return hashed == hashValue



class AuthMixIn(object):
    """
    Mix-in for authentication and authorization support.
    """

    async def verifyCredentials(self, user: User, password: str) -> bool:
        """
        Verify a password for the given user.
        """
        if user is None:
            authenticated = False
        else:
            try:
                if (
                    self.config.masterKey is not None and
                    password == self.config.masterKey
                ):
                    return True

                authenticated = user.verifyPlaintextPassword(password)
            except Exception:
                self.log.failure("Unable to check password")
                authenticated = False

        self.log.debug(
            "Valid credentials for {user}: {result}",
            user=user, result=authenticated,
        )

        return authenticated


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
            self.log.debug("Authentication failed")
            raise NotAuthenticatedError()


    async def authorizationsForUser(
        self, user: User, event: Optional[Event]
    ) -> Authorization:
        """
        Look up the authorizations that a user has for a given event.
        """
        async def matchACL(user: User, acl: Container[str]) -> bool:
            if "*" in acl:
                return True

            for shortName in user.shortNames:
                if "person:{}".format(shortName) in acl:
                    return True

            for group in (await user.groups()):
                if "position:{}".format(group.fullNames[0]) in acl:
                    return True

            return False

        authorizations = Authorization.none
        authorizations |= Authorization.readPersonnel
        authorizations |= Authorization.readIncidentReports
        authorizations |= Authorization.writeIncidentReports

        if user is not None:
            for shortName in user.shortNames:
                if shortName in self.config.IMSAdmins:
                    authorizations |= Authorization.imsAdmin

                if event is not None:
                    if (await matchACL(user, self.storage.writers(event))):
                        authorizations |= Authorization.writeIncidents
                        authorizations |= Authorization.readIncidents
                    else:
                        if (await matchACL(user, self.storage.readers(event))):
                            authorizations |= Authorization.readIncidents

        self.log.debug(
            "Authz for {user}: {authorizations}",
            user=user, authorizations=authorizations,
        )

        return authorizations


    async def authorizeRequest(
        self, request: IRequest, event: Optional[Event],
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
            self.log.debug(
                "Authorization failed for {request.user}. "
                "Requires {requiredAuthorizations}, has {userAuthorizations}. "
                "URI: {request.uri}",
                request=request,
                requiredAuthorizations=requiredAuthorizations,
                userAuthorizations=userAuthorizations,
            )
            raise NotAuthorizedError()


    async def authorizeRequestForIncidentReport(
        self, request: IRequest, number: int
    ) -> None:
        """
        Determine whether the user attached to a request has the required
        authorizations to read the incident report with the given number.
        """
        authFailure = None

        for event, _incidentNumber in (
            self.storage.incidentsAttachedToIncidentReport(number)
        ):
            # No incident attached; use the authorization for reading incidents
            # from the corresponding event.
            # Because it's possible for multiple incidents to be attached, if
            # one fails, keep trying the others in case they allow it.
            try:
                await self.authorizeRequest(
                    request, event, Authorization.readIncidents
                )
            except NotAuthorizedError as e:
                authFailure = e
            else:
                authFailure = None
                break
        else:
            # No incident attached
            await self.authorizeRequest(
                request, None, Authorization.readIncidentReports
            )

        if authFailure is not None:
            raise authFailure


    async def lookupUserName(self, username: str) -> Optional[User]:
        """
        Look up the user record for a user short name.
        """
        # FIXME: a hash would be better (eg. rangersByHandle)
        for ranger in await self.dms.personnel():
            if ranger.handle == username or username in ranger.email:
                break
        else:
            return None

        return User(ranger=ranger)


    @route(URLs.login.asText(), methods=("POST",))
    async def loginSubmit(self, request: IRequest) -> KleinRenderable:
        """
        Endpoint for a login form submission.
        """
        username = self.queryValue(request, "username")
        password = self.queryValue(request, "password", default="")

        if username is None:
            user = None
        else:
            user = await self.lookupUserName(username)

        if user is None:
            self.log.debug(
                "Login failed: no such user: {username}", username=username
            )
        else:
            authenticated = await self.verifyCredentials(user, password)

            if authenticated:
                session = request.getSession()
                session.user = user

                url = self.queryValue(request, "o")
                if url is None:
                    location = URLs.prefix  # Default to application home
                else:
                    location = URL.fromText(url)

                return self.redirect(request, location)
            else:
                self.log.debug(
                    "Login failed: incorrect credentials for user: {user}",
                    user=user
                )

        return self.login(request, failed=True)


    @route(URLs.login.asText(), methods=("HEAD", "GET"))
    def login(
        self, request: IRequest, failed: bool = False
    ) -> KleinRenderable:
        """
        Endpoint for the login page.
        """
        self.authenticateRequest(request, optional=True)

        return LoginPage(self, failed=failed)


    @route(URLs.logout.asText(), methods=("HEAD", "GET"))
    def logout(self, request: IRequest) -> KleinRenderable:
        """
        Endpoint for logging out.
        """
        session = request.getSession()
        session.expire()

        # Redirect back to application home
        return self.redirect(request, URLs.prefix)
