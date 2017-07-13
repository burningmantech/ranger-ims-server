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

from hashlib import sha1
from typing import Any, Iterable, Optional
from typing.io import BinaryIO

from attr import Factory, attrib, attrs
from attr.validators import instance_of

from twisted.logger import ILogObserver, Logger, globalLogPublisher
from twisted.python.filepath import FilePath
from twisted.web.iweb import IRequest

from ims.application._auth import AuthApplication, AuthProvider
from ims.application._eventsource import DataStoreEventSourceLogObserver
from ims.application._klein import notFoundResponse, router
from ims.application._urls import URLs
from ims.dms import DutyManagementSystem
from ims.ext.klein import ContentType, HeaderName, KleinRenderable
from ims.store import IMSDataStore

from .config import Configuration
from .external import ExternalMixIn
from .json import JSONMixIn
from .web import WebMixIn


__all__ = (
    "WebService",
)



@attrs(frozen=True)
class WebService(JSONMixIn, WebMixIn, ExternalMixIn):
    """
    Incident Management System web service.
    """

    log = _log = Logger()
    router = router


    config: Configuration = attrib(validator=instance_of(Configuration))

    storeObserver: ILogObserver = attrib(
        default=Factory(DataStoreEventSourceLogObserver), init=False
    )

    auth: AuthProvider = attrib(
        default=Factory(
            lambda self: AuthProvider(config=self.config), takes_self=True
        ),
        init=False,
    )
    _authApplication: AuthApplication = attrib(
        default=Factory(
            lambda self: AuthApplication(auth=self.auth, config=self.config),
            takes_self=True,
        ),
        init=False,
    )


    @property
    def storage(self) -> IMSDataStore:
        return self.config.storage


    @property
    def dms(self) -> DutyManagementSystem:
        return self.config.dms


    def __attrs_post_init__(self) -> None:
        globalLogPublisher.addObserver(self.storeObserver)


    def __del__(self) -> None:
        globalLogPublisher.removeObserver(self.storeObserver)


    #
    # Auth
    #

    @router.route(URLs.auth, branch=True)
    def authApplication(self, request: IRequest) -> KleinRenderable:
        """
        Auth resource.
        """
        return self._authApplication.router.resource()


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
        if etag is None:
            etag = sha1(data).hexdigest()
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
            return notFoundResponse(request)
