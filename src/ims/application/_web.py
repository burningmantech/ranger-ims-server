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

from typing import ClassVar, Optional

from attr import attrs

from hyperlink import URL

from twisted.web.iweb import IRequest

from ims.auth import Authorization
from ims.config import Configuration, URLs
from ims.element.admin.events import AdminEventsPage
from ims.element.admin.root import AdminRootPage
from ims.element.admin.streets import AdminStreetsPage
from ims.element.admin.types import AdminIncidentTypesPage
from ims.element.incident.incident import IncidentPage
from ims.element.incident.incident_template import IncidentTemplatePage
from ims.element.incident.queue import DispatchQueuePage
from ims.element.incident.queue_template import DispatchQueueTemplatePage
from ims.element.incident.report import IncidentReportPage
from ims.element.incident.report_template import IncidentReportTemplatePage
from ims.element.incident.reports import IncidentReportsPage
from ims.element.incident.reports_template import IncidentReportsTemplatePage
from ims.element.root import RootPage
from ims.ext.klein import KleinRenderable, static
from ims.model import Event
from ims.store import NoSuchIncidentReportError

from ._klein import Router, notFoundResponse, redirect


__all__ = (
    "WebApplication",
)


def _unprefix(url: URL) -> URL:
    prefix = URLs.app.path[:-1]
    assert url.path[:len(prefix)] == prefix, (url.path[len(prefix):], prefix)
    return url.replace(path=url.path[len(prefix):])



@attrs(frozen=True, auto_attribs=True, kw_only=True, cmp=False)
class WebApplication(object):
    """
    Application with web interface endpoints.
    """

    router: ClassVar[Router] = Router()

    config: Configuration

    #
    # Web interface
    #

    @router.route(_unprefix(URLs.app), methods=("HEAD", "GET"))
    def applicationRootResource(self, request: IRequest) -> KleinRenderable:
        """
        Application root page.
        """
        return RootPage(config=self.config)


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
        return AdminRootPage(config=self.config)


    @router.route(_unprefix(URLs.adminEvents), methods=("HEAD", "GET"))
    async def adminEventsPage(
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
        return AdminEventsPage(config=self.config)


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
        return AdminIncidentTypesPage(config=self.config)


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
        return AdminStreetsPage(config=self.config)


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
        return DispatchQueuePage(config=self.config, event=event)


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
        return DispatchQueueTemplatePage(config=self.config)


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

        return IncidentPage(
            config=self.config, event=event, number=numberValue
        )


    @router.route(
        _unprefix(URLs.viewIncidentTemplate), methods=("HEAD", "GET")
    )
    @static
    def viewIncidentTemplatePage(
        self, request: IRequest
    ) -> KleinRenderable:
        """
        Endpoint for the incident page template.
        """
        return IncidentTemplatePage(config=self.config)


    # FIXME: viewIncidentReports
    @router.route(_unprefix(URLs.viewIncidentReports), methods=("HEAD", "GET"))
    async def viewIncidentReportsPage(
        self, request: IRequest
    ) -> KleinRenderable:
        """
        Endpoint for the incident reports page.
        """
        await self.config.authProvider.authorizeRequest(
            request, None, Authorization.readIncidentReports
        )
        return IncidentReportsPage(config=self.config)


    @router.route(
        _unprefix(URLs.viewIncidentReportsTemplate), methods=("HEAD", "GET")
    )
    @static
    def viewIncidentReportsTemplatePage(
        self, request: IRequest
    ) -> KleinRenderable:
        """
        Endpoint for the incident reports page template.
        """
        return IncidentReportsTemplatePage(config=self.config)


    @router.route(
        _unprefix(URLs.viewIncidentReportNumber), methods=("HEAD", "GET")
    )
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

            try:
                incidentReport = (
                    await self.config.store.incidentReportWithNumber(
                        numberValue
                    )
                )
            except NoSuchIncidentReportError:
                await self.config.authProvider.authorizeRequest(
                    request, None, Authorization.readIncidentReports
                )
                return notFoundResponse(request)

            await self.config.authProvider.authorizeRequestForIncidentReport(
                request, incidentReport
            )

        return IncidentReportPage(config=self.config, number=numberValue)


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
        return IncidentReportTemplatePage(config=self.config)
