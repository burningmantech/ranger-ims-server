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

from typing import TYPE_CHECKING, ClassVar, cast

from attrs import Factory, field, frozen
from klein import KleinRenderable
from twisted.logger import globalLogPublisher
from twisted.python.filepath import FilePath
from twisted.web.iweb import IRequest
from twisted.web.static import File

import ims.element
from ims.config import Configuration, URLs
from ims.ext.json_ext import jsonTextFromObject
from ims.ext.klein import ContentType, HeaderName, static

from ._api import APIApplication
from ._auth import AuthApplication
from ._eventsource import DataStoreEventSourceLogObserver
from ._external import ExternalApplication  # type: ignore[attr-defined]
from ._klein import Router, redirect
from ._web import WebApplication


if TYPE_CHECKING:
    from twisted.web.resource import IResource


__all__ = ("MainApplication",)


resourcesDirectory = FilePath(ims.element.__file__).parent().child("static")


def apiApplicationFactory(parent: "MainApplication") -> APIApplication:
    return APIApplication(
        config=parent.config,
        storeObserver=parent.storeObserver,
    )


def authApplicationFactory(parent: "MainApplication") -> AuthApplication:
    return AuthApplication(config=parent.config)


def externalApplicationFactory(
    parent: "MainApplication",
) -> ExternalApplication:
    return ExternalApplication(config=parent.config)


def webApplicationFactory(parent: "MainApplication") -> WebApplication:
    return WebApplication(config=parent.config)


@frozen(kw_only=True, eq=False)
class MainApplication:
    """
    Incident Management System main application.
    """

    router: ClassVar[Router] = Router()

    config: Configuration

    storeObserver: DataStoreEventSourceLogObserver = field(
        factory=DataStoreEventSourceLogObserver, init=False
    )

    apiApplication: APIApplication = field(
        default=Factory(apiApplicationFactory, takes_self=True), init=False
    )

    authApplication: AuthApplication = field(
        default=Factory(authApplicationFactory, takes_self=True), init=False
    )

    externalApplication: ExternalApplication = field(
        default=Factory(externalApplicationFactory, takes_self=True),
        init=False,
    )

    webApplication: WebApplication = field(
        default=Factory(webApplicationFactory, takes_self=True), init=False
    )

    def __attrs_post_init__(self) -> None:
        globalLogPublisher.addObserver(self.storeObserver)

    def __del__(self) -> None:
        globalLogPublisher.removeObserver(self.storeObserver)

    #
    # Static content
    #

    @router.route(URLs.root, methods=("HEAD", "GET"))
    def rootEndpoint(self, request: IRequest) -> KleinRenderable:
        """
        Server root page.
        """
        return "IMS"

    @router.route(URLs.prefix, methods=("HEAD", "GET"))
    def prefixEndpoint(self, request: IRequest) -> KleinRenderable:
        """
        IMS root page.

        This redirects to the application root page.
        """
        return redirect(request, URLs.app)

    @router.route(URLs.static, branch=True)
    @static
    def staticEndpoint(self, request: IRequest) -> KleinRenderable:
        """
        Return endpoint for static resources collection.
        """
        return File(resourcesDirectory.path)

    #
    # URLs
    #

    @router.route(URLs.urlsJS, methods=("HEAD", "GET"))
    @static
    def urlsEndpoint(self, request: IRequest) -> KleinRenderable:
        """
        JavaScript variables for service URLs.
        """
        urls = {
            k: getattr(URLs, k).asText() for k in URLs.__dict__ if not k.startswith("_")
        }

        request.setHeader(HeaderName.contentType.value, ContentType.javascript.value)

        return "\n".join(
            (f"var url_{k} = {jsonTextFromObject(v)};" for k, v in urls.items())
        )

    #
    # Child application endpoints
    #

    @router.route(URLs.api, branch=True)
    def apiApplicationEndpoint(self, request: IRequest) -> KleinRenderable:
        """
        API application resource.
        """
        return self.apiApplication.router.resource()

    @router.route(URLs.authApp, branch=True)
    def authApplicationEndpoint(self, request: IRequest) -> KleinRenderable:
        """
        Auth application resource.
        """
        return self.authApplication.router.resource()

    @router.route(URLs.external, branch=True)
    def externalApplicationEndpoint(self, request: IRequest) -> KleinRenderable:
        """
        External application resource.
        """
        return cast("IResource", self.externalApplication.router.resource())

    @router.route(URLs.app, branch=True)
    def webApplicationEndpoint(self, request: IRequest) -> KleinRenderable:
        """
        Web application resource.
        """
        return self.webApplication.router.resource()
