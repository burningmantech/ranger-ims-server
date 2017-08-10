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
Incident Management System web interface.
"""

from typing import Optional

from attr import attrib, attrs
from attr.validators import instance_of

from hyperlink import URL

from twisted.web.iweb import IRequest

from ims.auth import Authorization
from ims.config import Configuration, URLs
from ims.element.admin import AdminPage
from ims.element.admin_acl import AdminAccessControlPage
from ims.element.admin_streets import AdminStreetsPage
from ims.element.admin_types import AdminIncidentTypesPage
from ims.element.incident import IncidentPage
from ims.element.incident_template import IncidentTemplatePage
from ims.element.queue import DispatchQueuePage
from ims.element.queue_template import DispatchQueueTemplatePage
from ims.element.report import IncidentReportPage
from ims.element.report_template import IncidentReportTemplatePage
from ims.element.root import RootPage
from ims.ext.klein import KleinRenderable, static
from ims.model import Event

from ._klein import Router, notFoundResponse, redirect

Optional  # silence linter


__all__ = (
    "WebApplication",
)


def _unprefix(url: URL) -> URL:
    prefix = URLs.app.path[:-1]
    assert url.path[:len(prefix)] == prefix, (url.path[len(prefix):], prefix)
    return url.replace(path=url.path[len(prefix):])



@attrs(frozen=True)
class WebApplication(object):
    """
    Application with web interface endpoints.
    """

    router = Router()

    config: Configuration = attrib(validator=instance_of(Configuration))

    #
    # Web interface
    #

    @router.route(_unprefix(URLs.app), methods=("HEAD", "GET"))
    def applicationRootResource(self, request: IRequest) -> KleinRenderable:
        """
        Application root page.
        """
        return RootPage(self.config)


    @router.route(_unprefix(URLs.viewEvent), methods=("HEAD", "GET"))
    def viewEventResource(
        self, request: IRequest, eventID: str
    ) -> KleinRenderable:
        """
        Event root page.

        This redirects to the event's dispatch queue page.
        """
        return redirect(request, URLs.viewDispatchQueueRelative)


    @router.route(_unprefix(URLs.admin), methods=("HEAD", "GET"))
    @static
    async def adminPage(self, request: IRequest) -> KleinRenderable:
        """
        Endpoint for admin page.
        """
        # FIXME: Not strictly required because the underlying data is
        # protected.
        # But the error you get is stupid, so let's avoid that for now.
        await self.config.authProvider.authorizeRequest(
            request, None, Authorization.imsAdmin
        )
        return AdminPage(self.config)


    @router.route(_unprefix(URLs.adminAccessControl), methods=("HEAD", "GET"))
    async def adminAccessControlPage(
        self, request: IRequest
    ) -> KleinRenderable:
        """
        Endpoint for access control page.
        """
        # FIXME: Not strictly required because the underlying data is
        # protected.
        # But the error you get is stupid, so let's avoid that for now.
        await self.config.authProvider.authorizeRequest(
            request, None, Authorization.imsAdmin
        )
        return AdminAccessControlPage(self.config)


    @router.route(_unprefix(URLs.adminIncidentTypes), methods=("HEAD", "GET"))
    async def adminAdminIncidentTypesPagePage(
        self, request: IRequest
    ) -> KleinRenderable:
        """
        Endpoint for incident types admin page.
        """
        # FIXME: Not strictly required because the underlying data is
        # protected.
        # But the error you get is stupid, so let's avoid that for now.
        await self.config.authProvider.authorizeRequest(
            request, None, Authorization.imsAdmin
        )
        return AdminIncidentTypesPage(self.config)


    @router.route(_unprefix(URLs.adminStreets), methods=("HEAD", "GET"))
    async def adminStreetsPage(self, request: IRequest) -> KleinRenderable:
        """
        Endpoint for streets admin page.
        """
        # FIXME: Not strictly required because the underlying data is
        # protected.
        # But the error you get is stupid, so let's avoid that for now.
        await self.config.authProvider.authorizeRequest(
            request, None, Authorization.imsAdmin
        )
        return AdminStreetsPage(self.config)


    @router.route(_unprefix(URLs.viewDispatchQueue), methods=("HEAD", "GET"))
    async def viewDispatchQueuePage(
        self, request: IRequest, eventID: str
    ) -> KleinRenderable:
        """
        Endpoint for the dispatch queue page.
        """
        event = Event(id=eventID)
        # FIXME: Not strictly required because the underlying data is
        # protected.
        # But the error you get is stupid, so let's avoid that for now.
        await self.config.authProvider.authorizeRequest(
            request, event, Authorization.readIncidents
        )
        return DispatchQueuePage(self.config, event)


    @router.route(
        _unprefix(URLs.viewDispatchQueueTemplate), methods=("HEAD", "GET")
    )
    @static
    def viewDispatchQueueTemplatePage(
        self, request: IRequest
    ) -> KleinRenderable:
        """
        Endpoint for the dispatch queue page template.
        """
        return DispatchQueueTemplatePage(self.config)


    @router.route(_unprefix(URLs.viewIncidentNumber), methods=("HEAD", "GET"))
    async def viewIncidentPage(
        self, request: IRequest, eventID: str, number: str
    ) -> KleinRenderable:
        """
        Endpoint for the incident page.
        """
        event = Event(id=eventID)

        numberValue: Optional[int]
        if number == "new":
            authz = Authorization.writeIncidents
            numberValue = None
        else:
            authz = Authorization.readIncidents
            try:
                numberValue = int(number)
            except ValueError:
                return notFoundResponse(request)

        await self.config.authProvider.authorizeRequest(request, event, authz)

        return IncidentPage(self.config, event, numberValue)


    @router.route(
        _unprefix(URLs.viewIncidentNumberTemplate), methods=("HEAD", "GET")
    )
    @static
    def viewIncidentNumberTemplatePage(
        self, request: IRequest
    ) -> KleinRenderable:
        """
        Endpoint for the incident page template.
        """
        return IncidentTemplatePage(self.config)


    # FIXME: viewIncidentReports


    @router.route(_unprefix(URLs.viewIncidentReport), methods=("HEAD", "GET"))
    async def viewIncidentReportPage(
        self, request: IRequest, number: str
    ) -> KleinRenderable:
        """
        Endpoint for the incident report page.
        """
        numberValue: Optional[int]
        if number == "new":
            await self.config.authProvider.authorizeRequest(
                request, None, Authorization.writeIncidentReports
            )
            numberValue = None
        else:
            try:
                numberValue = int(number)
            except ValueError:
                return notFoundResponse(request)

            await self.config.authProvider.authorizeRequestForIncidentReport(
                request, numberValue
            )

        return IncidentReportPage(self.config, numberValue)


    @router.route(
        _unprefix(URLs.viewIncidentReportTemplate), methods=("HEAD", "GET")
    )
    @static
    def viewIncidentReportTemplatePage(
        self, request: IRequest
    ) -> KleinRenderable:
        """
        Endpoint for the incident report page template.
        """
        return IncidentReportTemplatePage(self.config)
