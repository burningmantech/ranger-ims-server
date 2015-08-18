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
Authentication
"""

__all__ = [
    "guard",
]

from zope.interface import implementer, Interface

from twisted.logger import Logger
from twisted.cred.portal import IRealm, Portal
from twisted.cred.checkers import ANONYMOUS
from twisted.cred.credentials import (
    Anonymous as AnonymousCredentials,
    UsernamePassword as UsernamePasswordCredentials,
)
from twisted.cred.error import (
    LoginFailed as LoginFailedError, Unauthorized as UnauthorizedError
)
from twisted.web.iweb import IRequest
from twisted.web.http import UNAUTHORIZED
from twisted.web.server import Session, NOT_DONE_YET
from twisted.web.resource import IResource, Resource, ErrorPage
from twisted.web.util import DeferredResource
from twisted.web.template import flattenString

from .protocol import(
    NoAccessIncidentManagementSystem,
    # ReadOnlyIncidentManagementSystem,
    ReadWriteIncidentManagementSystem,
)
from .element.login import LoginPageElement



class IHTMLFormCredentialFactory(Interface):
    def credentials(request):
        pass



@implementer(IHTMLFormCredentialFactory)
class HTMLFormCredentialFactory(object):
    def credentials(self, request):
        try:
            username = request.args["username"][0]
            password = request.args["password"][0]
        except (KeyError, IndexError):
            raise LoginFailedError("No credentials")

        return UsernamePasswordCredentials(username, password)



class HTMLFormLoginResource(Resource):

    isLeaf = True

    def __init__(self, ims):
        Resource.__init__(self)
        self._ims = ims
        self._didFinish = False


    def _requestFinished(self, reason):
        self._didFinish = True


    def render(self, request):
        request.notifyFinish().addErrback(self._requestFinished)

        if self._didFinish:
            return None

        if request.method == b"GET":
            def write(body):
                request.write(body)
                request.finish()

            d = flattenString(request, LoginPageElement(self._ims))
            d.addCallback(write)

            return NOT_DONE_YET

        request.setResponseCode(UNAUTHORIZED)

        return "Unauthorized"



@implementer(IResource)
class HTMLFormSessionWrapper(object):

    log = Logger()

    isLeaf = False


    def __init__(self, portal, credentialFactories):
        self._portal = portal
        self._credentialFactories = credentialFactories


    def _authorizedResource(self, request):
        session = request.getSession()
        if hasattr(session, "avatar"):
            return session.avatar
        else:
            credentials = AnonymousCredentials()
            if request.method == b"POST":
                for credentialFactory in self._credentialFactories:
                    if IHTMLFormCredentialFactory.providedBy(
                        credentialFactory
                    ):
                        credentials = credentialFactory.credentials(request)
                        break

            request.method = "GET"
            return DeferredResource(self._login(credentials, request))


    def _login(self, credentials, request):
        def loginSucceeded((interface, avatar, logout)):
            return avatar

        def loginFailed(f):
            if f.check(UnauthorizedError, LoginFailedError):
                config = self._portal.realm.config
                ims = NoAccessIncidentManagementSystem(config)
                return HTMLFormLoginResource(ims)
            else:
                self.log.failure("Authentication error", failure=f)
                return ErrorPage(500, "Internal authentication error", None)

        # Pass request along as mind
        d = self._portal.login(credentials, request, IResource)
        d.addCallbacks(loginSucceeded, loginFailed)
        return d


    def getChildWithDefault(self, path, request):
        request.postpath.insert(0, request.prepath.pop())
        return self._authorizedResource(request)


    def putChild(path, child):
        raise NotImplementedError()


    def render(self, request):
        return self._authorizedResource(request).render(request)



@implementer(IRealm)
class Realm(object):

    def __init__(
        self, config, timeout=Session.sessionTimeout, logout=lambda: None
    ):
        self.config  = config
        self.timeout = timeout
        self.logout  = logout


    def requestAvatar(self, avatarId, mind, *interfaces):
        if IResource not in interfaces:
            raise NotImplementedError(
                "No known interfaces in {}".format(interfaces)
            )

        request = IRequest(mind)
        session = request.getSession()

        def logout():
            request.getSession().expire()

        if avatarId is ANONYMOUS:
            return (IResource, self.anonymousRoot(), logout)
        else:
            if not hasattr(session, "avatar"):
                ims = ReadWriteIncidentManagementSystem(self.config)
                ims.avatarId = avatarId
                session.sessionTimeout = self.timeout
                session.avatar = ims.app.resource()

                def expired():
                    del(session.avatar)

                session.notifyOnExpire(expired)

            return (IResource, session.avatar, logout)



def guard(config, realmName, checkers):
    portal = Portal(Realm(config), checkers)
    return HTMLFormSessionWrapper(portal, (HTMLFormCredentialFactory(),))
