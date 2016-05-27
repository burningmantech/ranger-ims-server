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

from functools import wraps
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

from twext.who.idirectory import RecordType, FieldName

from klein import Klein

from ims import __version__ as version
from ..tz import utcNow
from ..data.model import Incident, InvalidDataError
from ..data.json import textFromJSON, jsonFromFile
from ..data.json import rangerAsJSON, incidentAsJSON, incidentFromJSON
from ..data.edit import editIncident
from ..element.redirect import RedirectPage
from ..element.root import RootPage
from ..element.login import LoginPage
from ..element.queue import DispatchQueuePage
from ..element.queue_template import DispatchQueueTemplatePage
from ..element.incident import IncidentPage
from ..element.incident_template import IncidentTemplatePage
from ..dms import DatabaseError
from .auth import NotAuthenticatedError, NotAuthorizedError, Authorization
from .query import editsFromQuery



_app = Klein()

def route(*args, **kwargs):
    """
    Decorator that applies a Klein route and anything else we want applied to
    all endpoints.
    """
    def decorator(f):
        @_app.route(*args, **kwargs)
        @wraps(f)
        @inlineCallbacks
        def wrapper(self, request, *args, **kwargs):
            request.setHeader(
                HeaderName.server.value,
                "Incident Management System/{}".format(version),
            )
            try:
                response = yield f(self, request, *args, **kwargs)
            except (NotAuthenticatedError, NotAuthorizedError):
                returnValue(self.redirect(request, self.loginURL, origin=u"o"))
            except DatabaseError as e:
                self.log.error("DMS error: {failure}", failure=e)
            except Exception:
                self.log.failure("Request failed")
            else:
                returnValue(response)

            returnValue(self.internalErrorResource(request))

        return wrapper
    return decorator



if True:
    _fixedETag = version
else:
    # For debugging, change the ETag on every app start
    from uuid import uuid4
    _fixedETag = uuid4().hex


def fixedETag(f):
    """
    Decorator to add a fixed ETag to static resources.
    We use the IMS version number as the ETag, because they may change with new
    IMS versions, but should are otherwise static.
    """
    @wraps(f)
    def wrapper(self, request, *args, **kwargs):
        request.setHeader(HeaderName.etag.value, _fixedETag)
        return f(self, request, *args, **kwargs)

    return wrapper



class WebService(object):
    """
    Incident Management System web service.
    """

    log = Logger()
    app = _app

    sessionTimeout = Session.sessionTimeout

    #
    # URLs
    #

    prefixURL = URL.fromText(u"/ims")

    styleSheetURL = prefixURL.child(u"style.css")

    logoURL = prefixURL.child(u"logo.png")

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
    dataTablesBootstrapCSSURL = dataTablesBaseURL.child(
        u"media", u"css", u"dataTables.bootstrap.min.css"
    )
    dataTablesBootstrapJSURL = dataTablesBaseURL.child(
        u"media", u"js", u"dataTables.bootstrap.min.js"
    )

    momentJSURL = prefixURL.child(u"moment.min.js")

    imsJSURL      = prefixURL.child(u"ims.js")
    queueJSURL    = prefixURL.child(u"queue.js")
    incidentJSURL = prefixURL.child(u"incident.js")

    eventURL            = prefixURL.child(u"<event>")
    pingURL             = eventURL.child(u"ping")
    personnelURL        = eventURL.child(u"personnel")
    incidentTypesURL    = eventURL.child(u"incident_types")
    locationsURL        = eventURL.child(u"locations")
    incidentsURL        = eventURL.child(u"incidents")
    incidentNumberURL   = incidentsURL.child(u"<number>")

    viewDispatchQueueURL          = eventURL.child(u"queue")
    viewDispatchQueueTemplateURL  = prefixURL.child(u"_queue")
    viewDispatchQueueJSURL        = viewDispatchQueueURL.child(u"queue.js")
    dispatchQueueDataURL          = viewDispatchQueueURL.child(u"data")
    viewDispatchQueueRelativeURL  = URL.fromText(u"queue")
    viewIncidentsURL              = viewDispatchQueueURL.child(u"incidents")
    viewIncidentNumberURL         = viewIncidentsURL.child(u"<number>")
    viewIncidentNumberTemplateURL = prefixURL.child(u"_incident")

    #
    # External resource info
    #

    bootstrapVersionNumber  = u"3.3.6"
    jqueryVersionNumber     = u"2.2.0"
    dataTablesVersionNumber = u"1.10.11"
    momentVersionNumber     = u"2.13.0"

    bootstrapVersion  = u"bootstrap-{}-dist".format(bootstrapVersionNumber)
    jqueryVersion     = u"jquery-{}".format(jqueryVersionNumber)
    dataTablesVersion = u"DataTables-{}".format(dataTablesVersionNumber)
    momentVersion     = u"moment"

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

    momentJSSourceURL = URL.fromText(
        u"https://cdnjs.cloudflare.com/ajax/libs/moment.js/{n}/{v}.min.js"
        .format(n=momentVersionNumber, v=momentVersion)
    )


    def __init__(self, config):
        self.config = config
        self.storage = config.storage
        self.dms = config.dms
        self.directory = config.directory


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


    def authorizationsForUser(self, user, event):
        authorizations = Authorization.none

        if user is not None:
            if user.uid in self.config.readers:
                authorizations |= Authorization.readIncidents

            if user.uid in self.config.writers:
                authorizations |= Authorization.readIncidents
                authorizations |= Authorization.writeIncidents

        self.log.debug(
            "Authz for {user}: {authorizations}",
            user=user, authorizations=authorizations,
        )

        return authorizations


    def authorizeRequest(self, request, event, requiredAuthorizations):
        session = request.getSession()
        user = getattr(session, "user", None)

        userAuthorizations = self.authorizationsForUser(user, event)

        self.log.debug(
            "Authorizations for {user}: {authorizations}",
            user=user, authorizations=userAuthorizations,
        )

        if not (requiredAuthorizations & userAuthorizations):
            self.log.debug("Authorization failed for {user}", user=user)
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


    @route(loginURL.asText(), methods=("POST",))
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
                    location = self.prefixURL  # Default to application home
                else:
                    location = URL.fromText(url)

                returnValue(self.redirect(request, location))

        returnValue(self.login(request, failed=True))


    @route(loginURL.asText(), methods=("HEAD", "GET"))
    def login(self, request, failed=False):
        self.authenticateRequest(request, optional=True)

        return LoginPage(self, failed=failed)


    @route(logoutURL.asText(), methods=("HEAD", "GET"))
    def logout(self, request):
        session = request.getSession()
        session.expire()

        # Redirect back to application home
        return self.redirect(request, self.prefixURL)


    #
    # MIME type wrappers
    #

    def styleSheet(self, request, name, *names):
        request.setHeader(HeaderName.contentType.value, ContentType.CSS.value)
        return self.builtInResource(request, name, *names)


    def javaScript(self, request, name, *names):
        request.setHeader(
            HeaderName.contentType.value, ContentType.JavaScript.value
        )
        return self.builtInResource(request, name, *names)


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
        if etag is not None:
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
        else:
            message = u"{}".format(message).encode("utf-8")
        return self.textResource(request, message)


    def internalErrorResource(self, request, message=None):
        request.setResponseCode(http.INTERNAL_SERVER_ERROR)
        if message is None:
            message = "Internal error."
        else:
            message = u"{}".format(message).encode("utf-8")
        return self.textResource(request, message)


    #
    # Static content
    #

    @route(styleSheetURL.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def styleSheetResource(self, request):
        return self.styleSheet(request, "style.css")


    @route(logoURL.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def logoResource(self, request):
        request.setHeader(HeaderName.contentType.value, ContentType.PNG.value)
        return self.builtInResource(request, "logo.png")


    @route(bootstrapBaseURL.asText(), methods=("HEAD", "GET"), branch=True)
    @fixedETag
    def bootstrapResource(self, request):
        requestURL = URL.fromText(request.uri.rstrip("/"))

        # Remove URL prefix
        names = requestURL.path[len(self.bootstrapBaseURL.path):]

        request.setHeader(HeaderName.contentType.value, ContentType.CSS.value)
        return self.cachedZippedResource(
            request, self.bootstrapSourceURL, self.bootstrapVersion,
            self.bootstrapVersion, *names
        )


    @route(jqueryJSURL.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def jqueryJSResource(self, request):
        request.setHeader(
            HeaderName.contentType.value, ContentType.JavaScript.value
        )
        return self.cachedResource(
            request, self.jqueryJSSourceURL,
            "{}.min.js".format(self.jqueryVersion),
        )


    @route(jqueryMapURL.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def jqueryMapResource(self, request):
        request.setHeader(HeaderName.contentType.value, ContentType.JSON.value)
        return self.cachedResource(
            request, self.jqueryMapSourceURL,
            "{}.min.map".format(self.jqueryVersion),
        )


    @route(dataTablesBaseURL.asText(), methods=("HEAD", "GET"), branch=True)
    @fixedETag
    def dataTablesResource(self, request):
        requestURL = URL.fromText(request.uri.rstrip("/"))

        # Remove URL prefix
        names = requestURL.path[len(self.dataTablesBaseURL.path):]

        request.setHeader(HeaderName.contentType.value, ContentType.CSS.value)
        return self.cachedZippedResource(
            request, self.dataTablesSourceURL, self.dataTablesVersion,
            self.dataTablesVersion, *names
        )


    @route(momentJSURL.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def momentJSResource(self, request):
        request.setHeader(
            HeaderName.contentType.value, ContentType.JavaScript.value
        )
        return self.cachedResource(
            request, self.momentJSSourceURL,
            "{}.min.js".format(self.momentVersion),
        )


    @route(imsJSURL.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def imsJSResource(self, request):
        return self.javaScript(request, "ims.js")


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
        cacheDir = self.config.CachedResources

        if not cacheDir.isdir():
            cacheDir.createDirectory()

        destination = cacheDir.child(name)

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

    @route(u"/", methods=("HEAD", "GET"))
    def rootResource(self, request):
        """
        Server root page.

        This redirects to the application root page.
        """
        return self.redirect(request, self.prefixURL)


    @route(prefixURL.asText(), methods=("HEAD", "GET"))
    @route(prefixURL.asText() + u"/", methods=("HEAD", "GET"))
    @fixedETag
    def applicationRootResource(self, request):
        """
        Application root page.
        """
        self.authorizeRequest(request, None, Authorization.readIncidents)

        return RootPage(self)


    # Event root page; redirect to event dispatch queue

    @route(eventURL.asText(), methods=("HEAD", "GET"))
    @route(eventURL.asText() + u"/", methods=("HEAD", "GET"))
    def eventRootResource(self, request, event):
        """
        Event root page.

        This redirects to the event's dispatch queue page.
        """
        return self.redirect(request, self.viewDispatchQueueRelativeURL)


    #
    # JSON API endpoints
    #

    @route(pingURL.asText(), methods=("HEAD", "GET"))
    @route(pingURL.asText() + u"/", methods=("HEAD", "GET"))
    @fixedETag
    def pingResource(self, request, event):
        self.authenticateRequest(request)

        ack = b'"ack"'
        return self.jsonBytes(request, ack, bytes(hash(ack)))


    @route(personnelURL.asText(), methods=("HEAD", "GET"))
    @route(personnelURL.asText() + u"/", methods=("HEAD", "GET"))
    @inlineCallbacks
    def personnelResource(self, request, event):
        self.authorizeRequest(request, event, Authorization.readIncidents)

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


    @route(incidentTypesURL.asText(), methods=("HEAD", "GET"))
    @route(incidentTypesURL.asText() + u"/", methods=("HEAD", "GET"))
    def incidentTypesResource(self, request, event):
        self.authorizeRequest(request, event, Authorization.readIncidents)

        data = self.config.IncidentTypesJSONBytes
        return self.jsonBytes(request, data, bytes(hash(data)))


    @route(locationsURL.asText(), methods=("HEAD", "GET"))
    @route(locationsURL.asText() + u"/", methods=("HEAD", "GET"))
    def locationsResource(self, request, event):
        self.authorizeRequest(request, event, Authorization.readIncidents)

        data = self.config.locationsJSONBytes
        return self.jsonBytes(request, data, bytes(hash(data)))


    @route(incidentsURL.asText(), methods=("HEAD", "GET"))
    @route(incidentsURL.asText() + u"/", methods=("HEAD", "GET"))
    def listIncidentsResource(self, request, event):
        self.authorizeRequest(request, event, Authorization.readIncidents)

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


    @route(incidentsURL.asText(), methods=("POST",))
    @route(incidentsURL.asText() + u"/", methods=("POST",))
    def newIncidentResource(self, request, event):
        self.authorizeRequest(request, event, Authorization.readIncidents)

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
            "{}/{}".format(self.incidentNumberURL.asText(), number)
        )
        return self.noContentResource(request)


    @route(incidentNumberURL.asText(), methods=("HEAD", "GET"))
    def readIncidentResource(self, request, event, number):
        self.authorizeRequest(request, event, Authorization.readIncidents)

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


    @route(incidentNumberURL.asText(), methods=("POST",))
    def editIncidentResource(self, request, event, number):
        self.authorizeRequest(request, event, Authorization.readIncidents)

        try:
            number = int(number)
        except ValueError:
            return self.notFoundResource(request)

        author = request.user.decode("utf-8")

        storage = self.storage[event]

        incident = storage.readIncidentWithNumber(number)

        #
        # Apply the changes requested by the client
        #
        jsonEdits = jsonFromFile(request.content)
        try:
            edits = incidentFromJSON(jsonEdits, number=number, validate=False)
        except InvalidDataError as e:
            return self.badRequestResource(request, e)
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

    @route(viewDispatchQueueURL.asText(), methods=("HEAD", "GET"))
    @route(viewDispatchQueueURL.asText() + u"/", methods=("HEAD", "GET"))
    @fixedETag
    def viewDispatchQueuePage(self, request, event):
        self.authorizeRequest(request, event, Authorization.readIncidents)

        return DispatchQueuePage(self, event)


    @route(viewDispatchQueueTemplateURL.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def viewDispatchQueueTemplatePage(self, request):
        self.authenticateRequest(request, optional=True)

        return DispatchQueueTemplatePage(self)


    @route(queueJSURL.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def queueJSResource(self, request):
        return self.javaScript(request, "queue.js")


    @route(dispatchQueueDataURL.asText(), methods=("HEAD", "GET"))
    def dispatchQueueDataResource(self, request, event):
        self.authorizeRequest(request, event, Authorization.readIncidents)

        storage = self.storage[event]

        incidentNumbers = (number for number, etag in storage.listIncidents())

        stream = self.buildJSONArray(
            storage.readIncidentWithNumberRaw(number).encode("utf-8")
            for number in incidentNumbers
        )

        return self.jsonStream(request, stream, None)


    @route(viewIncidentNumberURL.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def viewIncidentPage(self, request, event, number):
        self.authorizeRequest(request, event, Authorization.readIncidents)

        if number == u"new":
            number = None
        else:
            try:
                number = int(number)
            except ValueError:
                return self.notFoundResource(request)

        return IncidentPage(self, event, number)


    @route(viewIncidentNumberURL.asText(), methods=("POST",))
    def editIncidentPage(self, request, event, number):
        self.authorizeRequest(
            request, event,
            Authorization.readIncidents | Authorization.writeIncidents
        )

        try:
            number = int(number)
        except ValueError:
            return self.notFoundResource(request)

        storage = self.storage[event]

        author = request.user
        edits = editsFromQuery(author, number, request)

        if edits:
            incident = storage.readIncidentWithNumber(number)
            edited = editIncident(incident, edits, author)

            self.log.info(
                u"User {author} edited incident #{number} via web",
                author=author, number=number
            )
            # self.log.debug(
            #     u"Original: {json}", json=incidentAsJSON(incident)
            # )
            self.log.debug(u"Changes: {json}", json=incidentAsJSON(edits))
            # self.log.debug(u"Edited: {json}", json=incidentAsJSON(edited))

            storage.writeIncident(edited)

        return IncidentPage(self, event, number)


    @route(viewIncidentNumberTemplateURL.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def viewIncidentNumberTemplatePage(self, request):
        self.authenticateRequest(request, optional=True)

        return IncidentTemplatePage(self)


    @route(incidentJSURL.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def incidentJSResource(self, request):
        return self.javaScript(request, "incident.js")



class HeaderName (Values):
    """
    Header names
    """

    server         = ValueConstant("Server")
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
