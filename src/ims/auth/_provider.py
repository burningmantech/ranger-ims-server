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

from typing import Container, FrozenSet, Optional, Sequence

from attr import attrib, attrs
from attr.validators import instance_of, optional

from twisted.logger import Logger
from twisted.python.constants import FlagConstant, Flags
from twisted.web.iweb import IRequest

from ims.dms import DMSError, DutyManagementSystem, verifyPassword
from ims.model import Event, Ranger
from ims.store import IMSDataStore

from ._exceptions import NotAuthenticatedError, NotAuthorizedError


__all__ = ()



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


    ranger: Ranger = attrib(validator=instance_of(Ranger))
    groups: Sequence[str] = attrib(validator=instance_of(tuple))


    @property
    def shortNames(self) -> Sequence[str]:
        return (self.ranger.handle,)


    def __str__(self) -> str:
        return str(self.ranger)



@attrs(frozen=True)
class AuthProvider(object):
    """
    Provider for authentication and authorization support.
    """

    _log = Logger()

    masterKey: Optional[str] = attrib(validator=optional(instance_of(str)))

    adminUsers: FrozenSet[str] = attrib()

    store: IMSDataStore = attrib(validator=instance_of(IMSDataStore))

    dms: DutyManagementSystem = attrib(
        validator=instance_of(DutyManagementSystem)
    )


    async def verifyCredentials(self, user: User, password: str) -> bool:
        """
        Verify a password for the given user.
        """
        if user is None:
            authenticated = False
        else:
            try:
                if (
                    self.masterKey is not None and
                    password == self.masterKey
                ):
                    return True

                hashedPassword = user.ranger.password
                if hashedPassword is None:
                    return False

                authenticated = verifyPassword(password, hashedPassword)
            except Exception:
                self._log.failure("Unable to check password")
                authenticated = False

        self._log.debug(
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
            self._log.debug("Authentication failed")
            raise NotAuthenticatedError()


    async def authorizationsForUser(
        self, user: User, event: Optional[Event]
    ) -> Authorization:
        """
        Look up the authorizations that a user has for a given event.
        """
        def matchACL(user: User, acl: Container[str]) -> bool:
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
        authorizations |= Authorization.readPersonnel
        authorizations |= Authorization.readIncidentReports
        authorizations |= Authorization.writeIncidentReports

        if user is not None:
            for shortName in user.shortNames:
                if shortName in self.adminUsers:
                    authorizations |= Authorization.imsAdmin

                if event is not None:
                    if matchACL(
                        user, frozenset(await self.store.writers(event))
                    ):
                        authorizations |= Authorization.writeIncidents
                        authorizations |= Authorization.readIncidents
                    else:
                        if matchACL(
                            user, frozenset(await self.store.readers(event))
                        ):
                            authorizations |= Authorization.readIncidents

        self._log.debug(
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
            self._log.debug(
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

        events = frozenset(
            event for event, _incidentNumber in
            await self.store.incidentsAttachedToIncidentReport(number)
        )

        for event in events:
            # There are incident attached; use the authorization for reading
            # incidents from the corresponding events.
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
        dms = self.dms

        # FIXME: a hash would be better (eg. rangersByHandle)
        try:
            rangers = tuple(await dms.personnel())
        except DMSError as e:
            self._log.critical("Unable to load personnel: {error}", error=e)
            return None

        for ranger in rangers:
            if ranger.handle == username:
                break
        else:
            for ranger in rangers:
                if username in ranger.email:
                    break
            else:
                return None

        positions = tuple(await dms.positions())

        groups = tuple(
            position.name for position in positions
            if ranger in position.members
        )

        return User(ranger=ranger, groups=groups)
