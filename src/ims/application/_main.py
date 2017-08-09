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
from twisted.python.filepath import FilePath
from twisted.web.iweb import IRequest
from twisted.web.static import File

import ims.element
from ims.config import Configuration, URLs
from ims.dms import DutyManagementSystem
from ims.ext.klein import KleinRenderable

from ._api import APIApplication
from ._auth import AuthApplication
from ._eventsource import DataStoreEventSourceLogObserver
from ._external import ExternalApplication
from ._klein import redirect, router
from ._web import WebApplication


__all__ = (
    "MainApplication",
)


resourcesDirectory = FilePath(ims.element.__file__).parent().child("static")



@attrs(frozen=True)
class MainApplication(object):
    """
    Incident Management System main application.
    """

    log = _log = Logger()
    router = router


    config: Configuration = attrib(validator=instance_of(Configuration))

    storeObserver: ILogObserver = attrib(
        default=Factory(DataStoreEventSourceLogObserver), init=False
    )

    apiApplication: APIApplication = attrib(
        default=Factory(
            lambda self: APIApplication(
                config=self.config,
                storeObserver=self.storeObserver,
            ),
            takes_self=True,
        ),
        init=False,
    )

    authApplication: AuthApplication = attrib(
        default=Factory(
            lambda self: AuthApplication(config=self.config),
            takes_self=True,
        ),
        init=False,
    )

    externalApplication: ExternalApplication = attrib(
        default=Factory(
            lambda self: ExternalApplication(config=self.config),
            takes_self=True,
        ),
        init=False,
    )

    webApplication: WebApplication = attrib(
        default=Factory(
            lambda self: WebApplication(config=self.config),
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


    @router.route(URLs.static, branch=True)
    def static(self, request: IRequest) -> KleinRenderable:
        return File(resourcesDirectory.path)


    #
    # Child application endpoints
    #

    @router.route(URLs.api, branch=True)
    def apiApplicationEndpoint(self, request: IRequest) -> KleinRenderable:
        """
        API application resource.
        """
        return self.apiApplication.router.resource()


    @router.route(URLs.auth, branch=True)
    def authApplicationEndpoint(self, request: IRequest) -> KleinRenderable:
        """
        Auth application resource.
        """
        return self.authApplication.router.resource()


    @router.route(URLs.external, branch=True)
    def externalApplicationEndpoint(
        self, request: IRequest
    ) -> KleinRenderable:
        """
        External application resource.
        """
        return self.externalApplication.router.resource()


    @router.route(URLs.app, branch=True)
    def webApplicationEndpoint(self, request: IRequest) -> KleinRenderable:
        """
        Web application resource.
        """
        return self.webApplication.router.resource()
