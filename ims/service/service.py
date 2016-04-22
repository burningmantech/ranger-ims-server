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
from twisted.web.client import downloadPage

from twext.who.idirectory import RecordType

from klein import Klein

from ..json import textFromJSON
from ..json import rangerAsJSON  # , incidentAsJSON, incidentFromJSON
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

    prefixURL        = URL.fromText(u"/ims")
    styleSheetURL    = prefixURL.child(u"style.css")
    favIconURL       = prefixURL.child(u"favicon.ico")
    logoURL          = prefixURL.child(u"logo.png")
    loginURL         = prefixURL.child(u"login")
    logoutURL        = prefixURL.child(u"logout")
    jqueryURL        = prefixURL.child(u"jquery")
    bootstrapURL     = prefixURL.child(u"bootstrap")
    datatablesURL    = prefixURL.child(u"datatables")
    eventURL         = prefixURL.child(u"<event>")
    pingURL          = eventURL.child(u"ping")
    personnelURL     = eventURL.child(u"personnel")
    incidentTypesURL = eventURL.child(u"incident_types")
    locationsURL     = eventURL.child(u"locations")

    bootstrapVersionNumber  = u"3.3.6"
    jqueryVersionNumber     = u"2.2.3"
    dataTablesVersionNumber = u"1.10.11"

    bootstrapVersion  = u"bootstrap-{}-dist".format(bootstrapVersionNumber)
    jqueryVersion     = u"jquery-{}".format(jqueryVersionNumber)
    dataTablesVersion = u"jquery.dataTables-{}".format(dataTablesVersionNumber)

    bootstrapSourceURL = URL.fromText(
        u"https://github.com/twbs/bootstrap/releases/download/v{n}/{v}.zip"
        .format(n=bootstrapVersionNumber, v=bootstrapVersion)
    )

    jqueryJSSourceURL = URL.fromText(
        u"https://code.jquery.com/{v}.min.js"
        .format(n=jqueryVersionNumber, v=jqueryVersion)
    )

    jqueryMapSourceURL = URL.fromText(
        u"https://code.jquery.com/{v}.min.map"
        .format(n=jqueryVersionNumber, v=jqueryVersion)
    )

    dataTablesJSSourceURL = URL.fromText(
        u"https://cdn.datatables.net/{n}/js/jquery.dataTables.min.js"
        .format(n=dataTablesVersionNumber, v=dataTablesVersion)
    )

    dataTablesCSSSourceURL = URL.fromText(
        u"https://cdn.datatables.net/{n}/css/jquery.dataTables.min.css"
        .format(n=dataTablesVersionNumber, v=dataTablesVersion)
    )


    def __init__(self, config):
        self.config = config
        self.storage = config.storage
        self.dms = config.dms
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
        return self.builtInResource(request, name, *names)


    # def javaScript(self, request, name, *names):
    #     request.setHeader("Content-Type", "application/javascript")
    #     return self.builtInResource(request, name, *names)


    # def javaScripSourceMap(self, request, name, *names):
    #     request.setHeader("Content-Type", "application/json")
    #     return self.builtInResource(request, name, *names)


    def jsonData(self, request, json, etag=None):
        request.setHeader("Content-Type", "application/json")
        if etag is not None:
            request.setHeader("ETag", etag)
        return textFromJSON(json)


    def jsonStream(self, request, jsonStream, etag=None):
        request.setHeader("Content-Type", "application/json")
        if etag is not None:
            request.setHeader("ETag", etag)
        for line in jsonStream:
            request.write(line)


    @staticmethod
    def buildJSONArray(items):
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

    def textResource(self, request, message):
        message = message
        request.setHeader("Content-Type", "text/plain")
        request.setHeader("ETag", bytes(hash(message)))
        return message.encode("utf-8")


    def notFoundResource(self, request):
        request.setResponseCode(http.NOT_FOUND)
        return self.textResource(request, "Not found.")


    def invalidQueryResource(self, request, arg, value):
        request.setResponseCode(http.BAD_REQUEST)
        return self.textResource(
            request, "Invalid query: {}={}".format(arg, value)
        )


    #
    # Static content
    #

    @app.route(styleSheetURL.asText())
    def style(self, request):
        return self.styleSheet(request, "style.css")


    @app.route(favIconURL.asText())
    def favIcon(self, request):
        request.setHeader("Content-Type", "image/x-icon")
        return self.builtInResource(request, "favicon.ico")


    @app.route(logoURL.asText())
    def logo(self, request):
        request.setHeader("Content-Type", "image/png")
        return self.builtInResource(request, "logo.png")


    @app.route(bootstrapURL.asText(), branch=True)
    def bootstrap(self, request):
        requestURL = URL.fromText(request.uri.rstrip("/"))

        # Remove URL prefix, add file prefix
        names = requestURL.path[len(self.bootstrapURL.path):]

        request.setHeader("Content-Type", "text/css")
        return self.cachedZippedResource(
            request, self.bootstrapSourceURL, self.bootstrapVersion,
            self.bootstrapVersion, *names
        )


    @app.route(jqueryURL.child(u"jquery.min.js").asText())
    def jqueryJS(self, request):
        request.setHeader("Content-Type", "application/javascript")
        return self.cachedResource(
            request, self.jqueryJSSourceURL,
            "{}.min.js".format(self.jqueryVersion),
        )


    @app.route(jqueryURL.child(u"jquery.min.map").asText())
    def jqueryMap(self, request):
        request.setHeader("Content-Type", "application/json")
        return self.cachedResource(
            request, self.jqueryMapSourceURL,
            "{}.min.map".format(self.jqueryVersion),
        )


    @app.route(datatablesURL.child(u"jquery.dataTables.min.js").asText())
    def datatablesJS(self, request):
        request.setHeader("Content-Type", "application/javascript")
        return self.cachedResource(
            request, self.dataTablesJSSourceURL,
            "{}.min.js".format(self.dataTablesVersion),
        )


    @app.route(datatablesURL.child(u"jquery.dataTables.min.css").asText())
    def datatablesCSS(self, request):
        request.setHeader("Content-Type", "text/css")
        return self.cachedResource(
            request, self.dataTablesCSSSourceURL,
            "{}.min.css".format(self.dataTablesVersion),
        )


    #
    # File access
    #

    _elementsRoot = FilePath(__file__).parent().parent().child("element")

    def builtInResource(self, request, name, *names):
        filePath = self._elementsRoot.child(name)

        for name in names:
            filePath = filePath.child(name)

        try:
            return filePath.getContent()
        except IOError:
            self.log.error(
                "File not found: {filePath.path}", filePath=filePath
            )
            return self.notFoundResource(request)


    def zippedResource(self, request, archiveName, name, *names):
        archivePath = self._elementsRoot.child("{0}.zip".format(archiveName))

        try:
            filePath = ZipArchive(archivePath.path)
        except IOError:
            self.log.error(
                "Zip archive not found: {archive.path}", archive=archivePath
            )
            return self.notFoundResource(request)
        except BadZipfile:
            self.log.error(
                "Bad zip archive: {archive.path}", archive=archivePath
            )
            return self.notFoundResource(request)

        filePath = filePath.child(name)
        for name in names:
            filePath = filePath.child(name)

        try:
            return filePath.getContent()
        except KeyError:
            self.log.error(
                "File not found in ZIP archive: {filePath.path}",
                filePath=filePath,
                archive=archivePath,
            )
            return self.notFoundResource(request)


    @inlineCallbacks
    def cacheFromURL(self, url, name):
        destination = self.config.CachedResources.child(name)

        if not destination.exists():
            tmp = destination.temporarySibling(extension=".tmp")
            try:
                yield downloadPage(
                    url.asText().encode("utf-8"), tmp.open("w")
                )
            except:
                self.log.failure("Download failed for {url}", url=url)
                try:
                    tmp.remove()
                except (OSError, IOError):
                    pass
            else:
                tmp.moveTo(destination)

        returnValue(destination)


    @inlineCallbacks
    def cachedResource(self, request, url, name):
        filePath = yield self.cacheFromURL(url, name)

        try:
            returnValue(filePath.getContent())
        except (OSError, IOError) as e:
            self.log.error(
                "Unable to open file {filePath.path}: {error}",
                filePath=filePath, error=e,
            )
            returnValue(self.notFoundResource(request))


    @inlineCallbacks
    def cachedZippedResource(self, request, url, archiveName, name, *names):
        archivePath = yield self.cacheFromURL(
            url, "{0}.zip".format(archiveName)
        )

        try:
            filePath = ZipArchive(archivePath.path)
        except BadZipfile as e:
            self.log.error(
                "Corrupt zip archive {archive.path}: {error}",
                archive=archivePath, error=e,
            )
            try:
                archivePath.remove()
            except (OSError, IOError):
                pass
            returnValue(self.notFoundResource(request))
        except (OSError, IOError) as e:
            self.log.error(
                "Unable to open zip archive {archive.path}: {error}",
                archive=archivePath, error=e,
            )
            returnValue(self.notFoundResource(request))

        filePath = filePath.child(name)
        for name in names:
            filePath = filePath.child(name)

        try:
            returnValue(filePath.getContent())
        except KeyError:
            self.log.error(
                "File not found in ZIP archive: {filePath.path}",
                filePath=filePath,
                archive=archivePath,
            )
            returnValue(self.notFoundResource(request))


    #
    # Web interface
    #

    @app.route(u"/")
    def rootResource(self, request):
        return self.redirect(request, self.prefixURL)


    @app.route(prefixURL.asText())
    @app.route(prefixURL.asText() + u"/")
    @authorized(Authorization.readIncidents)
    def homeResource(self, request):
        return RootPage(self)


    @app.route(eventURL.asText())
    @app.route(eventURL.asText() + u"/")
    def eventResource(self, request, event):
        return self.redirect(request, URL.fromText(u"queue"))


    @app.route(pingURL.asText())
    @app.route(pingURL.asText() + u"/")
    @authenticated()
    def pingResource(self, request, event):
        ack = b"ack"
        return self.jsonData(request, ack, bytes(hash(ack)))


    @app.route(personnelURL.asText())
    @app.route(personnelURL.asText() + u"/")
    @authorized(Authorization.readIncidents)
    @inlineCallbacks
    def personnelResource(self, request, event):
        stream, etag = yield self.personnelData()
        returnValue(self.jsonStream(request, stream, etag))


    @inlineCallbacks
    def personnelData(self):
        personnel = yield self.dms.personnel()
        returnValue((
            self.buildJSONArray(
                textFromJSON(rangerAsJSON(ranger)).encode("utf-8")
                for ranger in personnel
            ),
            bytes(hash(personnel)),
        ))


    @app.route(incidentTypesURL.asText())
    @app.route(incidentTypesURL.asText() + u"/")
    @authorized(Authorization.readIncidents)
    def incidentTypesResource(self, request, event):
        json = self.config.IncidentTypesJSONBytes
        return self.jsonStream(request, (json,), bytes(hash(json)))


    @app.route(locationsURL.asText())
    @app.route(locationsURL.asText() + u"/")
    @authorized(Authorization.readIncidents)
    def locationsResource(self, request, event):
        json = self.config.locationsJSONBytes
        return self.jsonStream(request, (json,), bytes(hash(json)))
