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

from zipfile import BadZipfile

from twisted.logger import globalLogPublisher
from twisted.python.filepath import FilePath
from twisted.python.zippath import ZipArchive

from .auth import AuthMixIn
from .eventsource import DataStoreEventSourceLogObserver
from .external import ExternalMixIn
from .http import ContentType, HeaderName
from .json import JSONMixIn
from .klein import KleinService
from .web import WebMixIn


__all__ = (
    "WebService",
)



class WebService(
    KleinService, AuthMixIn, JSONMixIn, WebMixIn, ExternalMixIn
):
    """
    Incident Management System web service.
    """

    def __init__(self, config):
        """
        @param config: The configuration to use.
        """
        self.config = config
        self.storage = config.storage
        self.dms = config.dms
        self.directory = config.directory

        self.storeObserver = DataStoreEventSourceLogObserver()
        globalLogPublisher.addObserver(self.storeObserver)


    def __del__(self):
        globalLogPublisher.removeObserver(self.storeObserver)


    #
    # MIME type wrappers
    #

    def styleSheet(self, request, name, *names):
        """
        Respond with a style sheet.
        """
        request.setHeader(HeaderName.contentType.value, ContentType.CSS.value)
        return self.builtInResource(request, name, *names)


    def javaScript(self, request, name, *names):
        """
        Respond with JavaScript.
        """
        request.setHeader(
            HeaderName.contentType.value, ContentType.JavaScript.value
        )
        return self.builtInResource(request, name, *names)


    # def javaScriptSourceMap(self, request, name, *names):
    #     """
    #     Respond with a JavaScript source map.
    #     """
    #     request.setHeader(
    #         HeaderName.contentType.value, ContentType.JSON.value
    #     )
    #     return self.builtInResource(request, name, *names)


    def jsonBytes(self, request, data, etag=None):
        """
        Respond with encoded JSON text.
        """
        request.setHeader(HeaderName.contentType.value, ContentType.JSON.value)
        if etag is not None:
            request.setHeader(HeaderName.etag.value, etag)
        return data


    def jsonStream(self, request, jsonStream, etag=None):
        """
        Respond with a stream of JSON data.
        """
        request.setHeader(HeaderName.contentType.value, ContentType.JSON.value)
        if etag is not None:
            request.setHeader(HeaderName.etag.value, etag)
        for line in jsonStream:
            request.write(line)


    @staticmethod
    def buildJSONArray(items):
        """
        Generate a JSON array from an iterable of JSON objects.
        """
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
    # File access
    #

    _elementsRoot = FilePath(__file__).parent().parent().child("element")

    def builtInResource(self, request, name, *names):
        """
        Respond with data from a local file.
        """
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
        """
        Respond with data from within a local zip file.
        """
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
