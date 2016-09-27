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

__all__ = [
    "Authorization",
    "AuthMixIn",
]

from twisted.python.constants import FlagConstant, Flags
from twisted.python.url import URL
from twisted.internet.defer import inlineCallbacks, returnValue

from twext.who.idirectory import RecordType, FieldName

from ..element.login import LoginPage
from .klein import route
from .urls import URLs
from .error import NotAuthenticatedError, NotAuthorizedError



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



class AuthMixIn(object):
    """
    Mix-in for authentication and authorization support.
    """

    @inlineCallbacks
    def verifyCredentials(self, user, password):
        if user is None:
            authenticated = False
        else:
            try:
                authenticated = yield user.verifyPlaintextPassword(password)
            except Exception:
                self.log.failure("Unable to check password")
                authenticated = False

        self.log.debug(
            "Valid credentials for {user}: {result}",
            user=user, result=authenticated,
        )

        returnValue(authenticated)


    def authenticateRequest(self, request, optional=False):
        session = request.getSession()
        request.user = getattr(session, "user", None)

        if request.user is None and not optional:
            self.log.debug("Authentication failed")
            raise NotAuthenticatedError()


    @inlineCallbacks
    def authorizationsForUser(self, user, event):
        @inlineCallbacks
        def matchACL(user, acl):
            acl = set(acl)

            if u"*" in acl:
                returnValue(True)

            for shortName in user.shortNames:
                if u"person:{}".format(shortName) in acl:
                    returnValue(True)

            for group in (yield user.groups()):
                if u"position:{}".format(group.fullNames[0]) in acl:
                    returnValue(True)

            returnValue(False)

        authorizations = Authorization.none
        authorizations |= Authorization.readPersonnel
        authorizations |= Authorization.readIncidentReports
        authorizations |= Authorization.writeIncidentReports

        if user is not None:
            for shortName in user.shortNames:
                if shortName in self.config.IMSAdmins:
                    authorizations |= Authorization.imsAdmin

                if event:
                    if (yield matchACL(user, self.storage.writers(event))):
                        authorizations |= Authorization.writeIncidents
                        authorizations |= Authorization.readIncidents
                    else:
                        if (yield matchACL(user, self.storage.readers(event))):
                            authorizations |= Authorization.readIncidents

        self.log.debug(
            "Authz for {user}: {authorizations}",
            user=user, authorizations=authorizations,
        )

        returnValue(authorizations)


    @inlineCallbacks
    def authorizeRequest(self, request, event, requiredAuthorizations):
        self.authenticateRequest(request)

        userAuthorizations = yield self.authorizationsForUser(
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


    @inlineCallbacks
    def authorizeRequestForIncidentReport(self, request, number):
        authFailure = None

        for event, incidentNumber in (
            self.storage.incidentsAttachedToIncidentReport(number)
        ):
            # No incident attached; use the authorization for reading incidents
            # from the corresponding event.
            # Because it's possible for multiple incidents to be attached, if
            # one fails, keep trying the others in case they allow it.
            try:
                yield self.authorizeRequest(
                    request, event, Authorization.readIncidents
                )
            except NotAuthorizedError as e:
                authFailure = e
            else:
                authFailure = None
                break
        else:
            # No incident attached
            yield self.authorizeRequest(
                request, None, Authorization.readIncidentReports
            )

        if authFailure is not None:
            raise authFailure


    def lookupUserName(self, username):
        return self.directory.recordWithShortName(RecordType.user, username)


    @inlineCallbacks
    def lookupUserEmail(self, email):
        user = None

        # Try lookup by email address
        for record in (yield self.directory.recordsWithFieldValue(
            FieldName.emailAddresses, email
        )):
            if user is not None:
                # More than one record with the same email address.
                # We can't know which is the right one, so none is.
                user = None
                break
            user = record

        returnValue(user)


    @route(URLs.login.asText(), methods=("POST",))
    @inlineCallbacks
    def loginSubmit(self, request):
        username = self.queryValue(request, u"username")
        password = self.queryValue(request, u"password", default=u"")

        if username is None:
            user = None
        else:
            user = yield self.lookupUserName(username)
            if user is None:
                user = yield self.lookupUserEmail(username)

        if user is None:
            self.log.debug(
                "Login failed: no such user: {username}", username=username
            )
        else:
            authenticated = yield self.verifyCredentials(user, password)

            if authenticated:
                session = request.getSession()
                session.user = user

                url = self.queryValue(request, u"o")
                if url is None:
                    location = URLs.prefix  # Default to application home
                else:
                    location = URL.fromText(url)

                returnValue(self.redirect(request, location))
            else:
                self.log.debug(
                    "Login failed: incorrect credentials for user: {user}",
                    user=user
                )

        returnValue((yield self.login(request, failed=True)))


    @route(URLs.login.asText(), methods=("HEAD", "GET"))
    def login(self, request, failed=False):
        self.authenticateRequest(request, optional=True)

        return LoginPage(self, failed=failed)


    @route(URLs.logout.asText(), methods=("HEAD", "GET"))
    def logout(self, request):
        session = request.getSession()
        session.expire()

        # Redirect back to application home
        return self.redirect(request, URLs.prefix)
