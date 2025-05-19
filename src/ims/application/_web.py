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
from klein._app import KleinSynchronousRenderable
from twisted.web.iweb import IRequest

from ims.config import Configuration, URLs
from ims.element.admin.events import AdminEventsPage
from ims.element.admin.itypes import AdminIncidentTypesPage
from ims.element.admin.root import AdminRootPage
from ims.element.admin.streets import AdminStreetsPage
from ims.element.incident.incident import IncidentPage
from ims.element.incident.incidents import IncidentsPage
from ims.element.incident.report import FieldReportPage
from ims.element.incident.reports import FieldReportsPage
from ims.element.root import RootPage
from ims.model import Event

from ._klein import Router, redirect


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

    @router.route(_unprefix(URLs.app), methods=("HEAD", "GET"))
    def applicationRootResource(self, request: IRequest) -> KleinRenderable:
        """
        Application root page.
        """
        return RootPage(config=self.config)

    @router.route(_unprefix(URLs.viewEvent), methods=("HEAD", "GET"))
    async def viewIncidentsResource(
        self, request: IRequest, event_id: str
    ) -> KleinSynchronousRenderable:
        """
        Event root page.

        This redirects to the event's incidents page.
        """
        return redirect(request, URLs.viewIncidentsRelative)

    @router.route(_unprefix(URLs.admin), methods=("HEAD", "GET"))
    async def adminPage(self, request: IRequest) -> KleinSynchronousRenderable:
        """
        Endpoint for admin page.
        """
        return AdminRootPage(config=self.config)

    @router.route(_unprefix(URLs.adminEvents), methods=("HEAD", "GET"))
    async def adminEventsPage(self, request: IRequest) -> KleinSynchronousRenderable:
        """
        Endpoint for access control page.
        """
        return AdminEventsPage(config=self.config)

    @router.route(_unprefix(URLs.adminIncidentTypes), methods=("HEAD", "GET"))
    async def adminAdminIncidentTypesPagePage(
        self, request: IRequest
    ) -> KleinSynchronousRenderable:
        """
        Endpoint for incident types admin page.
        """
        return AdminIncidentTypesPage(config=self.config)

    @router.route(_unprefix(URLs.adminStreets), methods=("HEAD", "GET"))
    async def adminStreetsPage(self, request: IRequest) -> KleinSynchronousRenderable:
        """
        Endpoint for streets admin page.
        """
        return AdminStreetsPage(config=self.config)

    @router.route(_unprefix(URLs.viewIncidents), methods=("HEAD", "GET"))
    async def viewIncidentsPage(
        self, request: IRequest, event_id: str
    ) -> KleinSynchronousRenderable:
        """
        Endpoint for the incidents page.
        """
        event = Event(id=event_id)
        return IncidentsPage(config=self.config, event=event)

    @router.route(_unprefix(URLs.viewIncidentNumber), methods=("HEAD", "GET"))
    async def viewIncidentPage(
        self, request: IRequest, event_id: str, number: str
    ) -> KleinSynchronousRenderable:
        """
        Endpoint for the incident page.
        """
        event = Event(id=event_id)
        return IncidentPage(config=self.config, event=event)

    @router.route(_unprefix(URLs.viewFieldReports), methods=("HEAD", "GET"))
    async def viewFieldReportsPage(
        self, request: IRequest, event_id: str
    ) -> KleinSynchronousRenderable:
        """
        Endpoint for the field reports page.
        """
        event = Event(id=event_id)
        return FieldReportsPage(config=self.config, event=event)

    @router.route(_unprefix(URLs.viewFieldReportNumber), methods=("HEAD", "GET"))
    async def viewFieldReportPage(
        self, request: IRequest, event_id: str, number: str
    ) -> KleinSynchronousRenderable:
        """
        Endpoint for the field report page.
        """
        config = self.config
        event = Event(id=event_id)
        return FieldReportPage(config=config, event=event)
