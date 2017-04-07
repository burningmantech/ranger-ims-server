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

from twisted.internet.defer import inlineCallbacks, returnValue

from .auth import Authorization
from .http import ContentType, HeaderName, staticResource
from .klein import route
from .urls import URLs
from ..data.model import Event
from ..element.admin import AdminPage
from ..element.admin_acl import AdminAccessControlPage
from ..element.admin_streets import AdminStreetsPage
from ..element.admin_types import AdminIncidentTypesPage
from ..element.incident import IncidentPage
from ..element.incident_template import IncidentTemplatePage
from ..element.queue import DispatchQueuePage
from ..element.queue_template import DispatchQueueTemplatePage
from ..element.report import IncidentReportPage
from ..element.report_template import IncidentReportTemplatePage
from ..element.root import RootPage


__all__ = (
    "WebMixIn",
)



class WebMixIn(object):
    """
    Mix-in for web interface.
    """

    #
    # Static content
    #

    @route(URLs.styleSheet.asText(), methods=("HEAD", "GET"))
    @staticResource
    def styleSheetResource(self, request):
        """
        Endpoint for global style sheet.
        """
        return self.styleSheet(request, "style.css")


    @route(URLs.logo.asText(), methods=("HEAD", "GET"))
    @staticResource
    def logoResource(self, request):
        """
        Endpoint for logo.
        """
        request.setHeader(HeaderName.contentType.value, ContentType.PNG.value)
        return self.builtInResource(request, "logo.png")


    @route(URLs.imsJS.asText(), methods=("HEAD", "GET"))
    @staticResource
    def imsJSResource(self, request):
        """
        Endpoint for C{ims.js}.
        """
        return self.javaScript(request, "ims.js")


    #
    # Web interface
    #

    @route(URLs.root.asText(), methods=("HEAD", "GET"))
    def rootResource(self, request):
        """
        Server root page.

        This redirects to the application root page.
        """
        return self.redirect(request, URLs.prefix)


    @route(URLs.prefix.asText(), methods=("HEAD", "GET"))
    @staticResource
    def applicationRootResource(self, request):
        """
        Application root page.
        """
        return RootPage(self)


    @route(URLs.viewEvent.asText(), methods=("HEAD", "GET"))
    def viewEventResource(self, request, eventID):
        """
        Event root page.

        This redirects to the event's dispatch queue page.
        """
        return self.redirect(request, URLs.viewDispatchQueueRelative)


    @route(URLs.admin.asText(), methods=("HEAD", "GET"))
    @staticResource
    @inlineCallbacks
    def adminPage(self, request):
        """
        Endpoint for admin page.
        """
        # FIXME: Not strictly required because the underlying data is
        # protected.
        # But the error you get is stupid, so let's avoid that for now.
        yield self.authorizeRequest(request, None, Authorization.imsAdmin)
        returnValue(AdminPage(self))


    @route(URLs.adminJS.asText(), methods=("HEAD", "GET"))
    @staticResource
    def adminJSResource(self, request):
        """
        Endpoint for C{admin.js}.
        """
        return self.javaScript(request, "admin.js")

    @route(URLs.adminAccessControl.asText(), methods=("HEAD", "GET"))
    @inlineCallbacks
    def adminAccessControlPage(self, request):
        """
        Endpoint for access control page.
        """
        # FIXME: Not strictly required because the underlying data is
        # protected.
        # But the error you get is stupid, so let's avoid that for now.
        yield self.authorizeRequest(request, None, Authorization.imsAdmin)
        returnValue(AdminAccessControlPage(self))


    @route(URLs.adminAccessControlJS.asText(), methods=("HEAD", "GET"))
    @staticResource
    def adminAccessControlJSResource(self, request):
        """
        Endpoint for C{admin_acl.js}.
        """
        return self.javaScript(request, "admin_acl.js")


    @route(URLs.adminIncidentTypes.asText(), methods=("HEAD", "GET"))
    @inlineCallbacks
    def adminAdminIncidentTypesPagePage(self, request):
        """
        Endpoint for incident types admin page.
        """
        # FIXME: Not strictly required because the underlying data is
        # protected.
        # But the error you get is stupid, so let's avoid that for now.
        yield self.authorizeRequest(request, None, Authorization.imsAdmin)
        returnValue(AdminIncidentTypesPage(self))


    @route(URLs.adminIncidentTypesJS.asText(), methods=("HEAD", "GET"))
    @staticResource
    def adminAdminIncidentTypesPageJSResource(self, request):
        """
        Endpoint for C{admin_types.js}.
        """
        return self.javaScript(request, "admin_types.js")


    @route(URLs.adminStreets.asText(), methods=("HEAD", "GET"))
    @inlineCallbacks
    def adminStreetsPage(self, request):
        """
        Endpoint for streets admin page.
        """
        # FIXME: Not strictly required because the underlying data is
        # protected.
        # But the error you get is stupid, so let's avoid that for now.
        yield self.authorizeRequest(request, None, Authorization.imsAdmin)
        returnValue(AdminStreetsPage(self))


    @route(URLs.adminStreetsJS.asText(), methods=("HEAD", "GET"))
    @staticResource
    def adminStreetsJSResource(self, request):
        """
        Endpoint for C{admin_streets.js}.
        """
        return self.javaScript(request, "admin_streets.js")


    @route(URLs.viewDispatchQueue.asText(), methods=("HEAD", "GET"))
    @inlineCallbacks
    def viewDispatchQueuePage(self, request, eventID):
        """
        Endpoint for the dispatch queue page.
        """
        event = Event(eventID)
        # FIXME: Not strictly required because the underlying data is
        # protected.
        # But the error you get is stupid, so let's avoid that for now.
        yield self.authorizeRequest(
            request, event, Authorization.readIncidents
        )
        returnValue(DispatchQueuePage(self, event))


    @route(URLs.viewDispatchQueueTemplate.asText(), methods=("HEAD", "GET"))
    @staticResource
    def viewDispatchQueueTemplatePage(self, request):
        """
        Endpoint for the dispatch queue page template.
        """
        return DispatchQueueTemplatePage(self)


    @route(URLs.viewDispatchQueueJS.asText(), methods=("HEAD", "GET"))
    @staticResource
    def viewDispatchQueueJSResource(self, request):
        """
        Endpoint for C{queue.js}.
        """
        return self.javaScript(request, "queue.js")


    @route(URLs.viewIncidentNumber.asText(), methods=("HEAD", "GET"))
    @inlineCallbacks
    def viewIncidentPage(self, request, eventID, number):
        """
        Endpoint for the incident page.
        """
        event = Event(eventID)

        if number == "new":
            authz = Authorization.writeIncidents
            number = None
        else:
            authz = Authorization.readIncidents
            try:
                number = int(number)
            except ValueError:
                returnValue(self.notFoundResource(request))

        yield self.authorizeRequest(request, event, authz)

        returnValue(IncidentPage(self, event, number))


    @route(URLs.viewIncidentNumberTemplate.asText(), methods=("HEAD", "GET"))
    @staticResource
    def viewIncidentNumberTemplatePage(self, request):
        """
        Endpoint for the incident page template.
        """
        return IncidentTemplatePage(self)


    @route(URLs.viewIncidentNumberJS.asText(), methods=("HEAD", "GET"))
    @staticResource
    def incidentJSResource(self, request):
        """
        Endpoint for C{incident.js}.
        """
        return self.javaScript(request, "incident.js")


    # FIXME: viewIncidentReports


    @route(URLs.viewIncidentReport.asText(), methods=("HEAD", "GET"))
    @inlineCallbacks
    def viewIncidentReportPage(self, request, number):
        """
        Endpoint for the report page.
        """
        if number == "new":
            yield self.authorizeRequest(
                request, None, Authorization.writeIncidentReports
            )
            number = None
        else:
            try:
                number = int(number)
            except ValueError:
                returnValue(self.notFoundResource(request))

            yield self.authorizeRequestForIncidentReport(request, number)

        returnValue(IncidentReportPage(self, number))


    @route(URLs.viewIncidentReportTemplate.asText(), methods=("HEAD", "GET"))
    @staticResource
    def viewIncidentReportTemplatePage(self, request):
        """
        Endpoint for the incident page template.
        """
        return IncidentReportTemplatePage(self)


    @route(URLs.viewIncidentReportJS.asText(), methods=("HEAD", "GET"))
    @staticResource
    def viewIncidentReportJSResource(self, request):
        """
        Endpoint for C{report.js}.
        """
        return self.javaScript(request, "report.js")
