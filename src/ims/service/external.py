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
Incident Management System cached external resources.
"""

__all__ = [
    "ExternalMixIn",
]

from zipfile import BadZipfile

from twisted.python.zippath import ZipArchive
from twisted.python.url import URL
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.web.client import downloadPage

from .http import staticResource, HeaderName, ContentType
from .urls import URLs
from .klein import route



class ExternalMixIn(object):
    """
    Mix-in for cached external resources.
    """

    bootstrapVersionNumber  = u"3.3.7"
    jqueryVersionNumber     = u"3.1.0"
    dataTablesVersionNumber = u"1.10.12"
    momentVersionNumber     = u"2.14.1"
    lscacheVersionNumber    = u"1.0.5"

    bootstrapVersion  = u"bootstrap-{}-dist".format(bootstrapVersionNumber)
    jqueryVersion     = u"jquery-{}".format(jqueryVersionNumber)
    dataTablesVersion = u"DataTables-{}".format(dataTablesVersionNumber)
    momentVersion     = u"moment-{}".format(momentVersionNumber)
    lscacheVersion    = u"lscache-{}".format(lscacheVersionNumber)

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
        u"https://cdnjs.cloudflare.com/ajax/libs/moment.js/{n}/moment.min.js"
        .format(n=momentVersionNumber)
    )

    lscacheJSSourceURL = URL.fromText(
        u"https://raw.githubusercontent.com/pamelafox/lscache/{n}/"
        u"lscache.min.js"
        .format(n=lscacheVersionNumber)
    )


    @route(URLs.bootstrapBase.asText(), methods=("HEAD", "GET"), branch=True)
    @staticResource
    def bootstrapResource(self, request):
        requestURL = URL.fromText(request.uri)

        # Remove URL prefix
        names = requestURL.path[len(URLs.bootstrapBase.path) - 1:]

        request.setHeader(HeaderName.contentType.value, ContentType.CSS.value)
        return self.cachedZippedResource(
            request, self.bootstrapSourceURL, self.bootstrapVersion,
            self.bootstrapVersion, *names
        )


    @route(URLs.jqueryJS.asText(), methods=("HEAD", "GET"))
    @staticResource
    def jqueryJSResource(self, request):
        request.setHeader(
            HeaderName.contentType.value, ContentType.JavaScript.value
        )
        return self.cachedResource(
            request, self.jqueryJSSourceURL,
            "{}.min.js".format(self.jqueryVersion),
        )


    @route(URLs.jqueryMap.asText(), methods=("HEAD", "GET"))
    @staticResource
    def jqueryMapResource(self, request):
        request.setHeader(HeaderName.contentType.value, ContentType.JSON.value)
        return self.cachedResource(
            request, self.jqueryMapSourceURL,
            "{}.min.map".format(self.jqueryVersion),
        )


    @route(
        URLs.dataTablesBase.asText(), methods=("HEAD", "GET"), branch=True
    )
    @staticResource
    def dataTablesResource(self, request):
        requestURL = URL.fromText(request.uri)

        # Remove URL prefix
        names = requestURL.path[len(URLs.dataTablesBase.path) - 1:]

        request.setHeader(HeaderName.contentType.value, ContentType.CSS.value)
        return self.cachedZippedResource(
            request, self.dataTablesSourceURL, self.dataTablesVersion,
            self.dataTablesVersion, *names
        )


    @route(URLs.momentJS.asText(), methods=("HEAD", "GET"))
    @staticResource
    def momentJSResource(self, request):
        request.setHeader(
            HeaderName.contentType.value, ContentType.JavaScript.value
        )
        return self.cachedResource(
            request, self.momentJSSourceURL,
            "{}.min.js".format(self.momentVersion),
        )


    @route(URLs.lscacheJS.asText(), methods=("HEAD", "GET"))
    @staticResource
    def lscacheJSResource(self, request):
        request.setHeader(
            HeaderName.contentType.value, ContentType.JavaScript.value
        )
        return self.cachedResource(
            request, self.lscacheJSSourceURL,
            "{}.min.js".format(self.lscacheVersion),
        )


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
