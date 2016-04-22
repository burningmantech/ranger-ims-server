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
Incident Management System web service.
"""

__all__ = [
    "WebService",
]

from zipfile import BadZipfile

from twisted.python.filepath import FilePath
from twisted.python.zippath import ZipArchive
from twisted.python.url import URL
from twisted.logger import Logger
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.web import http
from twisted.web.server import Session

from twext.who.idirectory import RecordType

from klein import Klein

from ..json import textFromJSON
from ..element.redirect import RedirectPage
from ..element.root import RootPage
from ..element.login import LoginPage
from .auth import authenticated, authorized, Authorization



class WebService(object):
    """
    Incident Management System web service.
    """

    app = Klein()
    log = Logger()

    sessionTimeout = Session.sessionTimeout

    prefixURL     = URL.fromText(u"/ims")
    styleSheetURL = prefixURL.child(u"style.css")
    favIconURL    = prefixURL.child(u"favicon.ico")
    logoURL       = prefixURL.child(u"logo.png")
    loginURL      = prefixURL.child(u"login")
    logoutURL     = prefixURL.child(u"logout")
    jqueryURL     = prefixURL.child(u"jquery")
    bootstrapURL  = prefixURL.child(u"bootstrap")
    datatablesURL = prefixURL.child(u"datatables")

    bootstrapVersion  = u"bootstrap-3.3.6-dist"
    jqueryVersion     = u"jquery-2.2.0"
    dataTablesVersion = u"DataTables-1.10.10"


    def __init__(self):
        self.directory = None


    def resource(self):
        return self.app.resource()


    def redirect(self, request, location, origin=None):
        if origin is not None:
            location = location.set(origin, request.uri.decode("utf-8"))

        url = location.asText().encode("utf-8")

        request.setHeader("Content-Type", "text/html")
        request.setHeader("Location", url)
        request.setResponseCode(http.FOUND)

        return RedirectPage(self, location)


    #
    # Authentication & authorization
    #

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
            "Authentication for {user}: {result}",
            user=user, result=authenticated,
        )

        returnValue(authenticated)


    @inlineCallbacks
    def authorizationForUser(self, user):
        if user is None:
            returnValue(Authorization.none)

        # FIXME: Check clubhouse roles

        returnValue(
            Authorization.readIncidents |
            Authorization.writeIncidents
        )


    @app.route(loginURL.asText(), methods=("POST",))
    @inlineCallbacks
    def loginSubmit(self, request):
        username = request.args.get("username", [""])[0].decode("utf-8")
        password = request.args.get("password", [""])[0].decode("utf-8")

        user = yield self.directory.recordWithShortName(
            RecordType.user, username
        )

        authenticated = yield self.verifyCredentials(user, password)
        if not authenticated:
            user = None

        authorization = yield self.authorizationForUser(user)

        if user:
            session = request.getSession()
            session.user = username
            session.authorization = authorization

            url = request.args.get(u"o", [None])[0]
            if url is None:
                location = self.prefixURL  # Default to application home
            else:
                location = URL.fromText(url)

            returnValue(self.redirect(request, location))

        returnValue(self.login(request, failed=True))


    @app.route(loginURL.asText())
    @authenticated(optional=True)
    def login(self, request, failed=False):
        return LoginPage(self, failed=failed)


    @app.route(logoutURL.asText())
    def logout(self, request):
        session = request.getSession()
        session.expire()

        url = request.args.get(u"o", [None])[0]
        if url is None:
            location = self.prefixURL  # Default to application home
        else:
            location = URL.fromText(url)

        return self.redirect(request, location)


    #
    # MIME type wrappers
    #

    def styleSheet(self, request, name, *names):
        request.setHeader("Content-Type", "text/css")
        return self.builtInResource(name, *names)


    def javaScript(self, request, name, *names):
        request.setHeader("Content-Type", "application/javascript")
        return self.builtInResource(name, *names)


    def javaScripSourceMap(self, request, name, *names):
        request.setHeader("Content-Type", "application/json")
        return self.builtInResource(name, *names)


    def jsonData(self, request, json):
        request.setHeader("Content-Type", "application/json")
        return textFromJSON(json)


    def jsonStream(self, request, jsonStream):
        request.setHeader("Content-Type", "application/json")
        for line in jsonStream:
            request.write(line)


    @staticmethod
    def _buildJSONArray(items):
        first = True

        yield b'['

        for item in items:
            if first:
                first = False
            else:
                yield b","

            yield item

        yield b']'


    #
    # Error resources
    #

    def notFoundResource(self, request):
        request.setResponseCode(http.NOT_FOUND)
        request.setHeader("Content-Type", "text/plain")
        return b"Not found."


    def invalidQueryResource(self, request, arg, value):
        request.setResponseCode(http.BAD_REQUEST)
        request.setHeader("Content-Type", "text/plain")
        return b"Invalid query: {}={}".format(arg, value)


    #
    # Static content
    #

    @app.route(styleSheetURL.asText())
    def style(self, request):
        return self.styleSheet(request, "style.css")


    @app.route(favIconURL.asText())
    def favIcon(self, request):
        request.setHeader("Content-Type", "image/x-icon")
        return self.builtInResource("favicon.ico")


    @app.route(logoURL.asText())
    def logo(self, request):
        request.setHeader("Content-Type", "image/png")
        return self.builtInResource("logo.png")


    @app.route(bootstrapURL.asText(), branch=True)
    def bootstrap(self, request):
        url = URL.fromText(request.uri.rstrip("/"))

        # Remove URL prefix, add file prefix
        segments = url.path[len(self.bootstrapURL.path):]
        segments = (self.bootstrapVersion,) + segments

        request.setHeader("Content-Type", "text/css")
        return self.zippedResource(request, self.bootstrapVersion, segments)


    @app.route(jqueryURL.child(u"jquery.min.js").asText())
    def jqueryJS(self, request):
        return self.javaScript(
            request, "jquery", "{}.min.js".format(self.jqueryVersion)
        )


    @app.route(jqueryURL.child(u"jquery.min.map").asText())
    def jqueryMap(self, request):
        return self.javaScripSourceMap(
            request, "jquery", "{}.min.map".format(self.jqueryVersion)
        )


    @app.route(datatablesURL.asText(), branch=True)
    def datatables(self, request):
        url = URL.fromText(request.uri.rstrip("/"))

        # Remove URL prefix, add file prefix
        segments = url.path[len(self.datatablesURL.path):]
        segments = (self.dataTablesVersion, "media") + segments

        request.setHeader("Content-Type", "text/css")
        return self.zippedResource(request, self.dataTablesVersion, segments)


    #
    # File access
    #

    _elementsRoot = FilePath(__file__).parent().child("element")

    def builtInResource(self, name, *names):
        resource = self._elementsRoot.child(name)
        for name in names:
            resource = resource.child(name)
        return resource.getContent()


    def zippedResource(self, request, name, segments):
        archivePath = self._elementsRoot.child("{0}.zip".format(name))

        try:
            filePath = ZipArchive(archivePath.path)
        except IOError:
            self.log.error(
                "Missing zip archive: {archive.path}", archive=archivePath
            )
            return self.notFoundResource(request)
        except BadZipfile:
            self.log.error(
                "Bad zip archive: {archive.path}", archive=archivePath
            )
            return self.notFoundResource(request)

        for segment in segments:
            filePath = filePath.child(segment)

        try:
            return filePath.getContent()
        except KeyError:
            self.log.error(
                "Not found in ZIP archive: {filePath.path}",
                filePath=filePath,
                archive=archivePath,
            )
            return self.notFoundResource(request)


    #
    # Web interface
    #

    @app.route(u"/")
    @authenticated(optional=True)
    def root(self, request):
        return RootPage(self)


    @app.route(prefixURL.asText())
    @app.route(prefixURL.asText() + u"/")
    @authorized(Authorization.readIncidents)
    def application(self, request):
        return RootPage(self)
