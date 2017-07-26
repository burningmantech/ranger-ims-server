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

from attr import Factory, attrib, attrs
from attr.validators import instance_of

from twisted.logger import ILogObserver, Logger, globalLogPublisher
from twisted.web.iweb import IRequest

from ims.application._api import APIApplication
from ims.application._auth import AuthApplication, AuthProvider
from ims.application._config import Configuration
from ims.application._eventsource import DataStoreEventSourceLogObserver
from ims.application._klein import redirect, router
from ims.application._static import builtInResource, javaScript, styleSheet
from ims.application._urls import URLs
from ims.application._web import WebApplication
from ims.dms import DutyManagementSystem
from ims.ext.klein import ContentType, HeaderName, KleinRenderable, static

from .external import ExternalMixIn


__all__ = (
    "WebService",
)



@attrs(frozen=True)
class WebService(ExternalMixIn):
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

    authApplication: AuthApplication = attrib(
        default=Factory(
            lambda self: AuthApplication(auth=self.auth), takes_self=True
        ),
        init=False,
    )

    apiApplication: APIApplication = attrib(
        default=Factory(
            lambda self: APIApplication(
                config=self.config,
                storeObserver=self.storeObserver,
                auth=self.auth,
            ),
            takes_self=True,
        ),
        init=False,
    )

    webApplication: WebApplication = attrib(
        default=Factory(
            lambda self: WebApplication(
                config=self.config,
                auth=self.auth,
            ),
            takes_self=True,
        ),
        init=False,
    )


    @property
    def dms(self) -> DutyManagementSystem:
        return self.config.dms


    def __attrs_post_init__(self) -> None:
        globalLogPublisher.addObserver(self.storeObserver)


    def __del__(self) -> None:
        globalLogPublisher.removeObserver(self.storeObserver)


    #
    # Static content
    #

    @router.route(URLs.root, methods=("HEAD", "GET"))
    def rootResource(self, request: IRequest) -> KleinRenderable:
        """
        Server root page.

        This redirects to the application root page.
        """
        return redirect(request, URLs.app)


    @router.route(URLs.styleSheet, methods=("HEAD", "GET"))
    @static
    def styleSheetResource(self, request: IRequest) -> KleinRenderable:
        """
        Endpoint for global style sheet.
        """
        return styleSheet(request, "style.css")


    @router.route(URLs.logo, methods=("HEAD", "GET"))
    @static
    def logoResource(self, request: IRequest) -> KleinRenderable:
        """
        Endpoint for logo.
        """
        request.setHeader(HeaderName.contentType.value, ContentType.png.value)
        return builtInResource(request, "logo.png")


    @router.route(URLs.imsJS, methods=("HEAD", "GET"))
    @static
    def imsJSResource(self, request: IRequest) -> KleinRenderable:
        """
        Endpoint for C{ims.js}.
        """
        return javaScript(request, "ims.js")


    #
    # Child application endpoints
    #

    @router.route(URLs.auth, branch=True)
    def authApplicationEndpoint(self, request: IRequest) -> KleinRenderable:
        """
        Auth application resource.
        """
        return self.authApplication.router.resource()


    @router.route(URLs.api, branch=True)
    def apiApplicationEndpoint(self, request: IRequest) -> KleinRenderable:
        """
        API application resource.
        """
        return self.apiApplication.router.resource()


    @router.route(URLs.app, branch=True)
    def webApplicationEndpoint(self, request: IRequest) -> KleinRenderable:
        """
        Web application resource.
        """
        return self.webApplication.router.resource()
