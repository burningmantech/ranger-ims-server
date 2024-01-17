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

from typing import ClassVar

from attrs import Factory, field, frozen
from klein import KleinRenderable
from twisted.logger import globalLogPublisher
from twisted.web.iweb import IRequest

from ims.config import Configuration, URLs
from ims.ext.json import jsonTextFromObject
from ims.ext.klein import ContentType, HeaderName, static

from ._api import APIApplication
from ._eventsource import DataStoreEventSourceLogObserver
from ._klein import Router


__all__ = ("MainApplication",)


def apiApplicationFactory(parent: "MainApplication") -> APIApplication:
    return APIApplication(
        config=parent.config,
        storeObserver=parent.storeObserver,
    )


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

    def __attrs_post_init__(self) -> None:
        globalLogPublisher.addObserver(self.storeObserver)

    def __del__(self) -> None:
        globalLogPublisher.removeObserver(self.storeObserver)

    #
    # Static content
    #

    @router.route(URLs.root, methods=("HEAD", "GET"))
    @static
    def rootEndpoint(self, request: IRequest) -> KleinRenderable:
        """
        Server root page.
        """
        return "IMS"

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
            k: getattr(URLs, k).asText()
            for k in URLs.__dict__
            if not k.startswith("_")
        }

        request.setHeader(
            HeaderName.contentType.value, ContentType.javascript.value
        )

        return "\n".join(
            (f"var url_{k} = {jsonTextFromObject(v)};" for k, v in urls.items())
        )

    #
    # Child application endpoints
    #

    @router.route(URLs.api, branch=True)
    @static
    def apiApplicationEndpoint(self, request: IRequest) -> KleinRenderable:
        """
        API application resource.
        """
        return self.apiApplication.router.resource()
