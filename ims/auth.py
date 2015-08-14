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

from zope.interface import implementer

from twisted.logger import Logger
from twisted.cred.portal import IRealm, Portal
from twisted.cred.checkers import ANONYMOUS
from twisted.cred.credentials import Anonymous as AnonymousCredentials
from twisted.cred.error import (
    LoginFailed as LoginFailedError, Unauthorized as UnauthorizedError
)
from twisted.web.iweb import IRequest
from twisted.web.http import UNAUTHORIZED
from twisted.web.server import Session, NOT_DONE_YET
from twisted.web.resource import IResource, Resource, ErrorPage
from twisted.web.guard import DigestCredentialFactory
from twisted.web.util import DeferredResource
from twisted.web.template import flattenString

from ims.element.login import LoginPageElement



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

        if request.method == b"POST":
            return "Authenticate!"

        request.setResponseCode(UNAUTHORIZED)

        return ""



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
            # if request.method == b"POST":
            #     for credentialFactory in self._credentialFactories:
            #         if IHTMLFormCredentialFactory.implementedBy(
            #             credentialFactory
            #         ):
            #             credentials = credentialFactory.decode(request)
            #             break
            return DeferredResource(self._login(credentials, request))


    def _login(self, credentials, request):
        def loginSucceeded((interface, avatar, logout)):
            return avatar

        def loginFailed(f):
            if f.check(UnauthorizedError, LoginFailedError):
                return HTMLFormLoginResource(self._portal.realm.ims)
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
        self, kleinFactory, timeout=Session.sessionTimeout, logout=lambda: None
    ):
        self._kleinFactory = kleinFactory
        self._timeout = timeout
        self._logout = logout


    @property
    def ims(self):
        if not hasattr(self, "_ims"):
            self._ims = self._kleinFactory()
        return self._ims


    def requestAvatar(self, avatarId, mind, *interfaces):
        if IResource not in interfaces:
            raise NotImplementedError(
                "No known interfaces in {}".format(interfaces)
            )

        request = IRequest(mind)
        session = request.getSession()

        if avatarId is ANONYMOUS:
            return (IResource, self.anonymousRoot(), self._logout)
        else:
            if not hasattr(session, "avatar"):
                kleinContainer = self.ims
                kleinContainer.avatarId = avatarId
                session.sessionTimeout = self._timeout
                session.avatar = kleinContainer.app.resource()

                def expired():
                    del(session.avatar)

                session.notifyOnExpire(expired)

            return (IResource, session.avatar, self._logout)



def guard(kleinFactory, realmName, checkers):
    portal = Portal(Realm(kleinFactory), checkers)

    wrapper = HTMLFormSessionWrapper(
        portal, (DigestCredentialFactory("md5", realmName),)
    )

    return wrapper

    # class Realm(object):
    #     implements(IRealm)

    #     def requestAvatar(self, avatarId, mind, *interfaces):
    #         if IResource not in interfaces:
    #             raise NotImplementedError()

    #         kleinContainer = kleinFactory()
    #         kleinContainer.avatarId = avatarId

    #         return (IResource, kleinContainer.app.resource(), lambda: None)

    # portal = Portal(Realm(), checkers)

    # return HTTPAuthSessionWrapper(
    #     portal,
    #     (
    #         DigestCredentialFactory("md5", realmName),
    #     )
    # )
