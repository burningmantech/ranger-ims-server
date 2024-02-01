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

from typing import ClassVar

from attrs import frozen
from hyperlink import URL
from klein import KleinRenderable
from twisted.web.iweb import IRequest

from ims.auth import Authorization, NotAuthorizedError
from ims.config import Configuration, URLs
from ims.element.admin.events import AdminEventsPage
from ims.element.admin.root import AdminRootPage
from ims.element.admin.streets import AdminStreetsPage
from ims.element.admin.types import AdminIncidentTypesPage
from ims.element.incident.incident import IncidentPage
from ims.element.incident.incident_template import IncidentTemplatePage
from ims.element.incident.incidents import IncidentsPage
from ims.element.incident.incidents_template import IncidentsTemplatePage
from ims.element.incident.report import IncidentReportPage
from ims.element.incident.report_template import IncidentReportTemplatePage
from ims.element.incident.reports import IncidentReportsPage
from ims.element.incident.reports_template import IncidentReportsTemplatePage
from ims.element.root import RootPage
from ims.ext.klein import static
from ims.model import Event
from ims.store import NoSuchIncidentReportError

from ._klein import Router, notFoundResponse, redirect


__all__ = ("WebApplication",)


def _unprefix(url: URL) -> URL:
    prefix = URLs.app.path[:-1]
    assert url.path[: len(prefix)] == prefix, (url.path[len(prefix) :], prefix)
    return url.replace(path=url.path[len(prefix) :])


@frozen(kw_only=True, eq=False)
class WebApplication:
    """
    Application with web interface endpoints.
    """

    router: ClassVar[Router] = Router()

    config: Configuration

    #
    # Web interface
    #

    @router.route(_unprefix(URLs.app))
    def applicationRootResource(self, request: IRequest) -> KleinRenderable:
        """
        Application root page.
        """
        return RootPage(config=self.config)

    @router.route(_unprefix(URLs.viewEvent))
    async def viewIncidentsResource(
        self, request: IRequest, event_id: str
    ) -> KleinRenderable:
        """
        Event root page.

        This redirects to the event's incidents page.
        """
        try:
            await self.config.authProvider.authorizeRequest(
                request, event_id, Authorization.readIncidents
            )
            url = URLs.viewIncidentsRelative
        except NotAuthorizedError:
            await self.config.authProvider.authorizeRequest(
                request, event_id, Authorization.writeIncidentReports
            )
            url = URLs.viewIncidentReportsRelative

        return redirect(request, url)

    @router.route(_unprefix(URLs.admin))
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

    @router.route(_unprefix(URLs.adminEvents))
    async def adminEventsPage(self, request: IRequest) -> KleinRenderable:
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

    @router.route(_unprefix(URLs.adminIncidentTypes))
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

    @router.route(_unprefix(URLs.adminStreets))
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

    @router.route(_unprefix(URLs.viewIncidents))
    async def viewIncidentsPage(
        self, request: IRequest, event_id: str
    ) -> KleinRenderable:
        """
        Endpoint for the incidents page.
        """
        # FIXME: Not strictly required because the underlying data is
        # protected.
        # But the error you get is stupid, so let's avoid that for now.
        await self.config.authProvider.authorizeRequest(
            request, event_id, Authorization.readIncidents
        )
        event = Event(id=event_id)
        return IncidentsPage(config=self.config, event=event)

    @router.route(
        _unprefix(URLs.viewIncidentsTemplate)
    )
    @static
    def viewIncidentsTemplatePage(self, request: IRequest) -> KleinRenderable:
        """
        Endpoint for the incidents page template.
        """
        return IncidentsTemplatePage(config=self.config)

    @router.route(_unprefix(URLs.viewIncidentNumber))
    async def viewIncidentPage(
        self, request: IRequest, event_id: str, number: str
    ) -> KleinRenderable:
        """
        Endpoint for the incident page.
        """
        numberValue: int | None
        if number == "new":
            authz = Authorization.writeIncidents
            numberValue = None
        else:
            authz = Authorization.readIncidents
            try:
                numberValue = int(number)
            except ValueError:
                return notFoundResponse(request)

        await self.config.authProvider.authorizeRequest(
            request, event_id, authz
        )

        event = Event(id=event_id)
        return IncidentPage(config=self.config, event=event, number=numberValue)

    @router.route(_unprefix(URLs.viewIncidentTemplate))
    @static
    def viewIncidentTemplatePage(self, request: IRequest) -> KleinRenderable:
        """
        Endpoint for the incident page template.
        """
        return IncidentTemplatePage(config=self.config)

    @router.route(_unprefix(URLs.viewIncidentReports))
    async def viewIncidentReportsPage(
        self, request: IRequest, event_id: str
    ) -> KleinRenderable:
        """
        Endpoint for the incident reports page.
        """
        try:
            await self.config.authProvider.authorizeRequest(
                request, event_id, Authorization.readIncidents
            )
        except NotAuthorizedError:
            await self.config.authProvider.authorizeRequest(
                request, event_id, Authorization.writeIncidentReports
            )
        event = Event(id=event_id)
        return IncidentReportsPage(config=self.config, event=event)

    @router.route(
        _unprefix(URLs.viewIncidentReportsTemplate)
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
        _unprefix(URLs.viewIncidentReportNumber)
    )
    async def viewIncidentReportPage(
        self, request: IRequest, event_id: str, number: str
    ) -> KleinRenderable:
        """
        Endpoint for the incident report page.
        """
        incidentReportNumber: int | None
        config = self.config
        if number == "new":
            await config.authProvider.authorizeRequest(
                request, event_id, Authorization.writeIncidentReports
            )
            incidentReportNumber = None
            del number
        else:
            try:
                incidentReportNumber = int(number)
            except ValueError:
                return notFoundResponse(request)
            del number

            try:
                incidentReport = await config.store.incidentReportWithNumber(
                    event_id, incidentReportNumber
                )
            except NoSuchIncidentReportError:
                await config.authProvider.authorizeRequest(
                    request, event_id, Authorization.readIncidents
                )
                return notFoundResponse(request)

            await config.authProvider.authorizeRequestForIncidentReport(
                request, incidentReport
            )

        event = Event(id=event_id)
        return IncidentReportPage(
            config=config, event=event, number=incidentReportNumber
        )

    @router.route(
        _unprefix(URLs.viewIncidentReportTemplate)
    )
    @static
    def viewIncidentReportTemplatePage(
        self, request: IRequest
    ) -> KleinRenderable:
        """
        Endpoint for the incident report page template.
        """
        return IncidentReportTemplatePage(config=self.config)
