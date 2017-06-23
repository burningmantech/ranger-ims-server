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

from typing import Any, Iterable, Optional
from typing.io import BinaryIO
from zipfile import BadZipfile

from twisted.logger import globalLogPublisher
from twisted.python.filepath import FilePath
from twisted.python.zippath import ZipArchive
from twisted.web.iweb import IRequest

from ims.ext.klein import ContentType, HeaderName, KleinRenderable

from .config import Configuration
from .eventsource import DataStoreEventSourceLogObserver
from .external import ExternalMixIn
from .json import JSONMixIn
from .klein import KleinService
from .web import WebMixIn


__all__ = (
    "WebService",
)



class WebService(KleinService, JSONMixIn, WebMixIn, ExternalMixIn):
    """
    Incident Management System web service.
    """

    def __init__(self, config: Configuration) -> None:
        """
        @param config: The configuration to use.
        """
        self.config = config
        self.storage = config.storage
        self.dms = config.dms
        self.directory = config.directory

        self.storeObserver = DataStoreEventSourceLogObserver()
        globalLogPublisher.addObserver(self.storeObserver)


    def __del__(self) -> None:
        globalLogPublisher.removeObserver(self.storeObserver)


    #
    # MIME type wrappers
    #

    def styleSheet(
        self, request: IRequest, name: str, *names: str
    ) -> KleinRenderable:
        """
        Respond with a style sheet.
        """
        request.setHeader(HeaderName.contentType.value, ContentType.css.value)
        return self.builtInResource(request, name, *names)


    def javaScript(
        self, request: IRequest, name: str, *names: str
    ) -> KleinRenderable:
        """
        Respond with JavaScript.
        """
        request.setHeader(
            HeaderName.contentType.value, ContentType.javascript.value
        )
        return self.builtInResource(request, name, *names)


    def jsonBytes(
        self, request: IRequest, data: bytes, etag: Optional[str] = None
    ) -> bytes:
        """
        Respond with encoded JSON text.
        """
        request.setHeader(HeaderName.contentType.value, ContentType.json.value)
        if etag is not None:
            request.setHeader(HeaderName.etag.value, etag)
        return data


    def jsonStream(
        self, request: IRequest, jsonStream: BinaryIO,
        etag: Optional[str] = None,
    ) -> None:
        """
        Respond with a stream of JSON data.
        """
        request.setHeader(HeaderName.contentType.value, ContentType.json.value)
        if etag is not None:
            request.setHeader(HeaderName.etag.value, etag)
        for line in jsonStream:
            request.write(line)


    @staticmethod
    def buildJSONArray(items: Iterable[Any]) -> Iterable[Any]:
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

    def builtInResource(
        self, request: IRequest, name: str, *names: str
    ) -> KleinRenderable:
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


    def zippedResource(
        self, request: IRequest, archiveName: str, name: str, *names: str
    ) -> KleinRenderable:
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
