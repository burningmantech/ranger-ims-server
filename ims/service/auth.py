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

    readIncidents  = FlagConstant()
    writeIncidents = FlagConstant()

Authorization.none = Authorization.readIncidents ^ Authorization.readIncidents



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
        else:
            self.log.debug(
                "Authenticated as {request.user}", request=request
            )


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

        if user is not None:
            if event:
                if (yield matchACL(user, self.storage.writers(event))):
                    authorizations |= Authorization.readIncidents
                    authorizations |= Authorization.writeIncidents
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

        self.log.debug(
            "Authorizations for {user}: {authorizations}",
            user=request.user, authorizations=userAuthorizations,
        )

        if not (requiredAuthorizations & userAuthorizations):
            self.log.debug("Authorization failed for {user}", user=request.user)
            raise NotAuthorizedError()


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


    @route(URLs.loginURL.asText(), methods=("POST",))
    @inlineCallbacks
    def loginSubmit(self, request):
        username = request.args.get("username", [""])[0].decode("utf-8")
        password = request.args.get("password", [""])[0].decode("utf-8")

        user = yield self.lookupUserName(username)
        if user is None:
            user = yield self.lookupUserEmail(username)

        if user is not None:
            authenticated = yield self.verifyCredentials(user, password)

            if authenticated:
                session = request.getSession()
                session.user = user

                url = request.args.get(u"o", [None])[0]
                if url is None:
                    location = URLs.prefixURL  # Default to application home
                else:
                    location = URL.fromText(url)

                returnValue(self.redirect(request, location))

        returnValue((yield self.login(request, failed=True)))


    @route(URLs.loginURL.asText(), methods=("HEAD", "GET"))
    def login(self, request, failed=False):
        self.authenticateRequest(request, optional=True)

        return LoginPage(self, failed=failed)


    @route(URLs.logoutURL.asText(), methods=("HEAD", "GET"))
    def logout(self, request):
        session = request.getSession()
        session.expire()

        # Redirect back to application home
        return self.redirect(request, URLs.prefixURL)
