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

from __future__ import print_function

__all__ = [
    "WebService",
]

from zipfile import BadZipfile

from twisted.python.constants import Values, ValueConstant
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

from ..data import Incident
from ..json import textFromJSON, jsonFromFile
from ..json import rangerAsJSON, incidentAsJSON, incidentFromJSON
from ..edit import editIncident
from ..tz import utcNow
from ..element.redirect import RedirectPage
from ..element.root import RootPage
from ..element.login import LoginPage
from ..element.queue import DispatchQueuePage
from .auth import authenticated, authorized, Authorization
from .query import termsFromQuery, showClosedFromQuery, sinceFromQuery



class WebService(object):
    """
    Incident Management System web service.
    """

    app = Klein()
    log = Logger()

    sessionTimeout = Session.sessionTimeout

    prefixURL = URL.fromText(u"/ims")

    styleSheetURL = prefixURL.child(u"style.css")

    favIconURL = prefixURL.child(u"favicon.ico")
    logoURL    = prefixURL.child(u"logo.png")

    loginURL  = prefixURL.child(u"login")
    logoutURL = prefixURL.child(u"logout")

    jqueryBaseURL = prefixURL.child(u"jquery")
    jqueryJSURL   = jqueryBaseURL.child(u"jquery.min.js")
    jqueryMapURL  = jqueryBaseURL.child(u"jquery.min.map")

    bootstrapBaseURL = prefixURL.child(u"bootstrap")
    bootstrapCSSURL  = bootstrapBaseURL.child(u"css", u"bootstrap.min.css")
    bootstrapJSURL   = bootstrapBaseURL.child(u"js", u"bootstrap.min.js")

    dataTablesBaseURL = prefixURL.child(u"datatables")
    dataTablesJSURL = dataTablesBaseURL.child(
        u"media", u"js", u"jquery.dataTables.min.js"
    )
    dataTablesCSSURL = dataTablesBaseURL.child(
        u"media", u"css", u"jquery.dataTables.min.css"
    )

    eventURL                 = prefixURL.child(u"<event>")
    pingURL                  = eventURL.child(u"ping")
    personnelURL             = eventURL.child(u"personnel")
    incidentTypesURL         = eventURL.child(u"incident_types")
    locationsURL             = eventURL.child(u"locations")
    incidentsURL             = eventURL.child(u"incidents")
    incidentNumberURL        = incidentsURL.child(u"<number>")
    dispatchQueueURL         = eventURL.child(u"queue")
    dispatchQueueRelativeURL = URL.fromText(u"queue")

    bootstrapVersionNumber  = u"3.3.6"
    jqueryVersionNumber     = u"2.2.0"
    dataTablesVersionNumber = u"1.10.11"

    bootstrapVersion  = u"bootstrap-{}-dist".format(bootstrapVersionNumber)
    jqueryVersion     = u"jquery-{}".format(jqueryVersionNumber)
    dataTablesVersion = u"DataTables-{}".format(dataTablesVersionNumber)

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

    dataTablesSourceURL = URL.fromText(
        u"https://datatables.net/releases/DataTables-{n}.zip"
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

        request.setHeader(HeaderName.contentType.value, ContentType.HTML.value)
        request.setHeader(HeaderName.location.value, url)
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


    @app.route(loginURL.asText(), methods=("HEAD", "GET"))
    @authenticated(optional=True)
    def login(self, request, failed=False):
        return LoginPage(self, failed=failed)


    @app.route(logoutURL.asText(), methods=("HEAD", "GET"))
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
        request.setHeader(HeaderName.contentType.value, ContentType.CSS.value)
        return self.builtInResource(request, name, *names)


    # def javaScript(self, request, name, *names):
    #     request.setHeader(
    #         HeaderName.contentType.value, ContentType.JavaScript.value
    #     )
    #     return self.builtInResource(request, name, *names)


    # def javaScriptSourceMap(self, request, name, *names):
    #     request.setHeader(
    #         HeaderName.contentType.value, ContentType.JSON.value
    #     )
    #     return self.builtInResource(request, name, *names)


    def jsonData(self, request, json, etag=None):
        request.setHeader(HeaderName.contentType.value, ContentType.JSON.value)
        if etag is not None:
            request.setHeader(HeaderName.etag.value, etag)
        return textFromJSON(json)


    def jsonBytes(self, request, data, etag=None):
        request.setHeader(HeaderName.contentType.value, ContentType.JSON.value)
        if etag is not None:
            request.setHeader(HeaderName.etag.value, etag)
        return data


    def jsonStream(self, request, jsonStream, etag=None):
        request.setHeader(HeaderName.contentType.value, ContentType.JSON.value)
        if etag is not None:
            request.setHeader(HeaderName.etag.value, etag)
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

    def noContentResource(self, request, etag=None):
        request.setResponseCode(http.NO_CONTENT)
        request.setHeader(HeaderName.etag.value, etag)
        return b""


    def textResource(self, request, message):
        message = message
        request.setHeader(HeaderName.contentType.value, ContentType.text.value)
        request.setHeader(HeaderName.etag.value, bytes(hash(message)))
        return message.encode("utf-8")


    def notFoundResource(self, request):
        request.setResponseCode(http.NOT_FOUND)
        return self.textResource(request, "Not found.")


    def invalidQueryResource(self, request, arg, value):
        request.setResponseCode(http.BAD_REQUEST)
        return self.textResource(
            request, "Invalid query: {}={}".format(arg, value)
        )


    def badRequestResource(self, request, message=None):
        request.setResponseCode(http.BAD_REQUEST)
        if message is None:
            message = "Bad request."
        return self.textResource(request, message)


    #
    # Static content
    #

    @app.route(styleSheetURL.asText(), methods=("HEAD", "GET"))
    def style(self, request):
        return self.styleSheet(request, "style.css")


    @app.route(favIconURL.asText(), methods=("HEAD", "GET"))
    def favIcon(self, request):
        request.setHeader(HeaderName.contentType.value, ContentType.ICO.value)
        return self.builtInResource(request, "favicon.ico")


    @app.route(logoURL.asText(), methods=("HEAD", "GET"))
    def logo(self, request):
        request.setHeader(HeaderName.contentType.value, ContentType.PNG.value)
        return self.builtInResource(request, "logo.png")


    @app.route(bootstrapBaseURL.asText(), methods=("HEAD", "GET"), branch=True)
    def bootstrap(self, request):
        requestURL = URL.fromText(request.uri.rstrip("/"))

        # Remove URL prefix
        names = requestURL.path[len(self.bootstrapBaseURL.path):]

        request.setHeader(HeaderName.contentType.value, ContentType.CSS.value)
        return self.cachedZippedResource(
            request, self.bootstrapSourceURL, self.bootstrapVersion,
            self.bootstrapVersion, *names
        )


    @app.route(jqueryJSURL.asText(), methods=("HEAD", "GET"))
    def jqueryJS(self, request):
        request.setHeader(
            HeaderName.contentType.value, ContentType.JavaScript.value
        )
        return self.cachedResource(
            request, self.jqueryJSSourceURL,
            "{}.min.js".format(self.jqueryVersion),
        )


    @app.route(jqueryMapURL.asText(), methods=("HEAD", "GET"))
    def jqueryMap(self, request):
        request.setHeader(HeaderName.contentType.value, ContentType.JSON.value)
        return self.cachedResource(
            request, self.jqueryMapSourceURL,
            "{}.min.map".format(self.jqueryVersion),
        )


    @app.route(dataTablesBaseURL.asText(), methods=("HEAD", "GET"), branch=True)
    def dataTables(self, request):
        requestURL = URL.fromText(request.uri.rstrip("/"))

        # Remove URL prefix
        names = requestURL.path[len(self.dataTablesBaseURL.path):]

        request.setHeader(HeaderName.contentType.value, ContentType.CSS.value)
        return self.cachedZippedResource(
            request, self.dataTablesSourceURL, self.dataTablesVersion,
            self.dataTablesVersion, *names
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
    # Basic resources
    #

    @app.route(u"/", methods=("HEAD", "GET"))
    def rootResource(self, request):
        """
        Server root page.

        This redirects to the application root page.
        """
        return self.redirect(request, self.prefixURL)


    @app.route(prefixURL.asText(), methods=("HEAD", "GET"))
    @app.route(prefixURL.asText() + u"/", methods=("HEAD", "GET"))
    @authorized(Authorization.readIncidents)
    def applicationRootResource(self, request):
        """
        Application root page.
        """
        return RootPage(self)


    # Event root page; redirect to event dispatch queue

    @app.route(eventURL.asText(), methods=("HEAD", "GET"))
    @app.route(eventURL.asText() + u"/", methods=("HEAD", "GET"))
    def eventRootResource(self, request, event):
        """
        Event root page.

        This redirects to the event's dispatch queue page.
        """
        return self.redirect(request, self.dispatchQueueRelativeURL)


    #
    # JSON API endpoints
    #

    @app.route(pingURL.asText(), methods=("HEAD", "GET"))
    @app.route(pingURL.asText() + u"/", methods=("HEAD", "GET"))
    @authenticated()
    def pingResource(self, request, event):
        ack = b'"ack"'
        return self.jsonBytes(request, ack, bytes(hash(ack)))


    @app.route(personnelURL.asText(), methods=("HEAD", "GET"))
    @app.route(personnelURL.asText() + u"/", methods=("HEAD", "GET"))
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


    @app.route(incidentTypesURL.asText(), methods=("HEAD", "GET"))
    @app.route(incidentTypesURL.asText() + u"/", methods=("HEAD", "GET"))
    @authorized(Authorization.readIncidents)
    def incidentTypesResource(self, request, event):
        data = self.config.IncidentTypesJSONBytes
        return self.jsonBytes(request, data, bytes(hash(data)))


    @app.route(locationsURL.asText(), methods=("HEAD", "GET"))
    @app.route(locationsURL.asText() + u"/", methods=("HEAD", "GET"))
    @authorized(Authorization.readIncidents)
    def locationsResource(self, request, event):
        data = self.config.locationsJSONBytes
        return self.jsonBytes(request, data, bytes(hash(data)))


    @app.route(incidentsURL.asText(), methods=("HEAD", "GET"))
    @app.route(incidentsURL.asText() + u"/", methods=("HEAD", "GET"))
    @authorized(Authorization.readIncidents)
    def listIncidentsResource(self, request, event):
        if request.args:
            incidents = self.storage[event].searchIncidents(
                terms=termsFromQuery(request),
                showClosed=showClosedFromQuery(request),
                since=sinceFromQuery(request),
            )
        else:
            incidents = self.storage[event].listIncidents()

        # Reverse order here because we generally want the clients to load the
        # more recent incidents first.
        # FIXME: Probably that should just be client-side logic.
        incidents = sorted(
            incidents, cmp=lambda a, b: cmp(a[0], b[0]), reverse=True
        )

        stream = self.buildJSONArray(
            textFromJSON(incident).encode("utf-8")
            for incident in incidents
        )

        return self.jsonStream(request, stream, None)


    @app.route(incidentsURL.asText(), methods=("POST",))
    @app.route(incidentsURL.asText() + u"/", methods=("POST",))
    @authorized(Authorization.readIncidents)
    def newIncidentResource(self, request, event):
        number = self.storage[event].nextIncidentNumber()

        json = jsonFromFile(request.content)
        incident = incidentFromJSON(json, number=number, validate=False)

        now = utcNow()

        if incident.created is None:
            # No timestamp provided; add one.

            # Right now is a decent default, but if there's a report entry
            # that's older than now, that's a better pick.
            created = now
            if incident.report_entries is not None:
                for entry in incident.report_entries:
                    if entry.created < created:
                        created = entry.created

            incident.created = created
            self.log.info(
                "Adding created time {created} to new incident #{number}",
                created=incident.created, number=number
            )
        else:
            if incident.created > now:
                return self.badRequestResource(
                    "Created time {} is in the future. Current time is {}."
                    .format(incident.created, now)
                )

        author = request.user

        # Apply this new incident as changes to an empty incident so that
        # system report entries get added.
        # It also adds the author, so we don't need to do it here.
        incident = editIncident(
            Incident(
                number=incident.number,    # Must match
                created=incident.created,  # Must match
            ),
            incident,
            author
        )

        self.storage[event].writeIncident(incident)

        self.log.info(
            u"User {author} created new incident #{number} via JSON",
            author=author, number=number
        )
        self.log.debug(u"New: {json}", json=incidentAsJSON(incident))

        request.setHeader(HeaderName.incidentNumber.value, number)
        request.setHeader(
            HeaderName.location.value,
            self.incidentNumberURL.asText() + u"/" + number
        )


    @app.route(incidentNumberURL.asText(), methods=("HEAD", "GET"))
    @authorized(Authorization.readIncidents)
    def readIncidentResource(self, request, event, number):
        # # For simulating slow connections
        # import time
        # time.sleep(0.3)

        try:
            number = int(number)
        except ValueError:
            return self.notFoundResource(request)

        if False:
            #
            # This is faster, but doesn't benefit from any cleanup or
            # validation code, so it's only OK if we know all data in the
            # store is clean by this server version's standards.
            #
            text = self.storage[event].readIncidentWithNumberRaw(number)
        else:
            #
            # This parses the data from the store, validates it, then
            # re-serializes it.
            #
            incident = self.storage[event].readIncidentWithNumber(number)
            text = textFromJSON(incidentAsJSON(incident))

        etag = self.storage[event].etagForIncidentWithNumber(number)

        return self.jsonBytes(request, text.encode("utf-8"), etag)


    @app.route(incidentNumberURL.asText(), methods=("POST",))
    @authorized(Authorization.readIncidents)
    def editIncidentResource(self, request, event, number):
        try:
            number = int(number)
        except ValueError:
            return self.notFoundResource(request)

        author = request.user

        storage = self.storage[event]

        incident = storage.readIncidentWithNumber(number)

        #
        # Apply the changes requested by the client
        #
        jsonEdits = jsonFromFile(request.content)
        edits = incidentFromJSON(jsonEdits, number=number, validate=False)
        edited = editIncident(incident, edits, author)

        #
        # Write to disk
        #
        storage.writeIncident(edited)

        self.log.debug(
            u"User {author} edited incident #{number} via JSON",
            author=author, number=number
        )
        # self.log.debug(u"Original: {json}", json=incidentAsJSON(incident))
        self.log.debug(u"Changes: {json}", json=jsonEdits)
        # self.log.debug(u"Edited: {json}", json=incidentAsJSON(edited))

        etag = storage.etagForIncidentWithNumber(number)

        return self.noContentResource(request, etag)


    #
    # Web interface
    #

    @app.route(dispatchQueueURL.asText(), methods=("HEAD", "GET"))
    @app.route(dispatchQueueURL.asText() + u"/", methods=("HEAD", "GET"))
    @authorized(Authorization.readIncidents)
    def dispatchQueueResource(self, request, event):
        storage = self.storage[event]
        return DispatchQueuePage(self, storage, event)



class HeaderName (Values):
    """
    Header names
    """

    contentType    = ValueConstant("Content-Type")
    etag           = ValueConstant("ETag")
    incidentNumber = ValueConstant("Incident-Number")
    location       = ValueConstant("Location")



class ContentType (Values):
    """
    Content types
    """

    HTML       = ValueConstant("text/html; charset=utf-8")
    XHTML      = ValueConstant("application/xhtml+xml")
    CSS        = ValueConstant("text/css")
    JavaScript = ValueConstant("application/javascript")

    JSON       = ValueConstant("application/json")

    text       = ValueConstant("text/plain; charset=utf-8")

    PNG        = ValueConstant("image/png")
    ICO        = ValueConstant("image/x-icon")



if __name__ == "__main__":
    from .config import Configuration

    config = Configuration(None)
    service = WebService(config)

    for rule in service.app.url_map.iter_rules():
        methods = list(rule.methods)
        print(
            "{rule.rule} {methods} -> {rule.endpoint}"
            .format(rule=rule, methods=methods)
        )
