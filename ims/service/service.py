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

from twisted.python.filepath import FilePath
from twisted.python.zippath import ZipArchive
from twisted.python.url import URL
from twisted.logger import Logger
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.web import http
from twisted.web.server import Session
from twisted.web.client import downloadPage

from ..data.json import textFromJSON
from ..data.json import incidentAsJSON
from ..data.edit import editIncident
from ..element.redirect import RedirectPage
from ..element.queue import DispatchQueuePage
from ..element.queue_template import DispatchQueueTemplatePage
from ..element.incident import IncidentPage
from ..element.incident_template import IncidentTemplatePage
from ..element.root import RootPage
from .http import HeaderName, ContentType, fixedETag
from .urls import URLs
from .klein import application as _app, route
from .auth import Authorization, AuthMixIn
from .json import JSONMixIn
from .query import editsFromQuery



class WebService(URLs, AuthMixIn, JSONMixIn):
    """
    Incident Management System web service.
    """

    log = Logger()
    app = _app

    sessionTimeout = Session.sessionTimeout

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

    @route(URLs.styleSheetURL.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def styleSheetResource(self, request):
        return self.styleSheet(request, "style.css")


    @route(URLs.logoURL.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def logoResource(self, request):
        request.setHeader(HeaderName.contentType.value, ContentType.PNG.value)
        return self.builtInResource(request, "logo.png")


    @route(URLs.bootstrapBaseURL.asText(), methods=("HEAD", "GET"), branch=True)
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


    @route(URLs.jqueryJSURL.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def jqueryJSResource(self, request):
        request.setHeader(
            HeaderName.contentType.value, ContentType.JavaScript.value
        )
        return self.cachedResource(
            request, self.jqueryJSSourceURL,
            "{}.min.js".format(self.jqueryVersion),
        )


    @route(URLs.jqueryMapURL.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def jqueryMapResource(self, request):
        request.setHeader(HeaderName.contentType.value, ContentType.JSON.value)
        return self.cachedResource(
            request, self.jqueryMapSourceURL,
            "{}.min.map".format(self.jqueryVersion),
        )


    @route(
        URLs.dataTablesBaseURL.asText(), methods=("HEAD", "GET"), branch=True
    )
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


    @route(URLs.momentJSURL.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def momentJSResource(self, request):
        request.setHeader(
            HeaderName.contentType.value, ContentType.JavaScript.value
        )
        return self.cachedResource(
            request, self.momentJSSourceURL,
            "{}.min.js".format(self.momentVersion),
        )


    @route(URLs.imsJSURL.asText(), methods=("HEAD", "GET"))
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
    # Web interface
    #

    @route(u"/", methods=("HEAD", "GET"))
    def rootResource(self, request):
        """
        Server root page.

        This redirects to the application root page.
        """
        return self.redirect(request, self.prefixURL)


    @route(URLs.prefixURL.asText(), methods=("HEAD", "GET"))
    @route(URLs.prefixURL.asText() + u"/", methods=("HEAD", "GET"))
    @fixedETag
    def applicationRootResource(self, request):
        """
        Application root page.
        """
        self.authorizeRequest(request, None, Authorization.readIncidents)

        return RootPage(self)


    # Event root page; redirect to event dispatch queue

    @route(URLs.eventURL.asText(), methods=("HEAD", "GET"))
    @route(URLs.eventURL.asText() + u"/", methods=("HEAD", "GET"))
    def eventRootResource(self, request, event):
        """
        Event root page.

        This redirects to the event's dispatch queue page.
        """
        return self.redirect(request, self.viewDispatchQueueRelativeURL)


    @route(URLs.viewDispatchQueueURL.asText(), methods=("HEAD", "GET"))
    @route(URLs.viewDispatchQueueURL.asText() + u"/", methods=("HEAD", "GET"))
    @fixedETag
    def viewDispatchQueuePage(self, request, event):
        self.authorizeRequest(request, event, Authorization.readIncidents)

        return DispatchQueuePage(self, event)


    @route(URLs.viewDispatchQueueTemplateURL.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def viewDispatchQueueTemplatePage(self, request):
        self.authenticateRequest(request, optional=True)

        return DispatchQueueTemplatePage(self)


    @route(URLs.queueJSURL.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def queueJSResource(self, request):
        return self.javaScript(request, "queue.js")


    @route(URLs.dispatchQueueDataURL.asText(), methods=("HEAD", "GET"))
    def dispatchQueueDataResource(self, request, event):
        self.authorizeRequest(request, event, Authorization.readIncidents)

        storage = self.storage[event]

        incidentNumbers = (number for number, etag in storage.listIncidents())

        stream = self.buildJSONArray(
            storage.readIncidentWithNumberRaw(number).encode("utf-8")
            for number in incidentNumbers
        )

        return self.jsonStream(request, stream, None)


    @route(URLs.viewIncidentNumberURL.asText(), methods=("HEAD", "GET"))
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


    @route(URLs.viewIncidentNumberURL.asText(), methods=("POST",))
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


    @route(URLs.viewIncidentNumberTemplateURL.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def viewIncidentNumberTemplatePage(self, request):
        self.authenticateRequest(request, optional=True)

        return IncidentTemplatePage(self)


    @route(URLs.incidentJSURL.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def incidentJSResource(self, request):
        return self.javaScript(request, "incident.js")



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
