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

from hyperlink import URL

from twisted.logger import ILogObserver, Logger, globalLogPublisher
from twisted.python.failure import Failure
from twisted.python.filepath import FilePath
from twisted.web.iweb import IRequest
from twisted.web.template import renderElement

from werkzeug.exceptions import MethodNotAllowed, NotFound
from werkzeug.routing import RequestRedirect

from ims.dms import DutyManagementSystem
from ims.ext.klein import ContentType, HeaderName, KleinRenderable
from ims.store import IMSDataStore

from .auth import AuthApplication, AuthProvider
from .config import Configuration
from .error import NotAuthenticatedError, NotAuthorizedError
from .eventsource import DataStoreEventSourceLogObserver
from .external import ExternalMixIn
from .json import JSONMixIn
from .klein import (
    forbiddenResponse, internalErrorResponse, methodNotAllowedResponse,
    notFoundResponse, redirect, renderResponse, router,
)
from .urls import URLs
from .web import WebMixIn
from ...dms import DMSError


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
            lambda self: AuthProvider(config=self.config), takes_self=True,
        ),
        init=False,
    )
    _authApplication: AuthApplication = attrib(
        default=Factory(
            lambda self: AuthApplication(
                auth=self.auth,
                config=self.config,
            ),
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

    @router.route(URLs.auth.asText(), branch=True)
    def authApplication(self, request: IRequest) -> KleinRenderable:
        """
        Auth resource.
        """
        return self._authApplication.router.resource()


    #
    # Error handlers
    #

    @router.handle_errors(RequestRedirect)
    @renderResponse
    def requestRedirectError(
        self, request: IRequest, failure: Failure
    ) -> KleinRenderable:
        """
        Redirect.
        """
        url = URL.fromText(failure.value.args[0].decode("utf-8"))
        return redirect(request, url)


    @router.handle_errors(NotFound)
    @renderResponse
    def notFoundError(
        self, request: IRequest, failure: Failure
    ) -> KleinRenderable:
        """
        Not found.
        """
        # Require authentication.
        # This is because exposing what resources do or do not exist can expose
        # information that was not meant to be exposed.
        self.auth.authenticateRequest(request)
        return notFoundResponse(request)


    @router.handle_errors(MethodNotAllowed)
    @renderResponse
    def methodNotAllowedError(
        self, request: IRequest, failure: Failure
    ) -> KleinRenderable:
        """
        HTTP method not allowed.
        """
        # Require authentication.
        # This is because exposing what resources do or do not exist can expose
        # information that was not meant to be exposed.
        self.auth.authenticateRequest(request)
        return methodNotAllowedResponse(request)


    @router.handle_errors(NotAuthorizedError)
    @renderResponse
    def notAuthorizedError(
        self, request: IRequest, failure: Failure
    ) -> KleinRenderable:
        """
        Not authorized.
        """
        return forbiddenResponse(request)


    @router.handle_errors(NotAuthenticatedError)
    @renderResponse
    def notAuthenticatedError(
        self, request: IRequest, failure: Failure
    ) -> KleinRenderable:
        """
        Not authenticated.
        """
        element = redirect(request, URLs.login, origin="o")
        return renderElement(request, element)


    @router.handle_errors(DMSError)
    @renderResponse
    def dmsError(
        self, request: IRequest, failure: Failure
    ) -> KleinRenderable:
        """
        DMS error.
        """
        self._log.failure("DMS error", failure)
        return internalErrorResponse(request)


    @router.handle_errors
    @renderResponse
    def unknownError(
        self, request: IRequest, failure: Failure
    ) -> KleinRenderable:
        """
        Deal with a request error caught by Klein.
        """
        # This logs the failure traceback for debugging.
        # Klein normally will also display the traceback in the response.
        # We don't do that for a few reasons:
        #  - It's a poor security practice to explain to an attacker what
        #    exactly is causing an internal error.
        #  - Most users don't know what to do with that inforrmation.
        #  - The admins should be able to find the errors in the logs.
        #  - Klein doing that is a developer feature; developers can also watch
        #    the logs.
        #  - The traceback is emitted after whatever else was sent with the
        #    request, which often means that it displays like a total mess in
        #    a browser, and that's just pitiful.
        self._log.failure("Request failed", failure)
        return internalErrorResponse(request)


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
