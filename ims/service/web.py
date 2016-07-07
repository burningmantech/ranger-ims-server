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

__all__ = [
    "WebMixIn",
]

from twisted.internet.defer import inlineCallbacks, returnValue

from ..element.admin import AdminPage
from ..element.admin_acl import AdminAccessControlPage
from ..element.admin_types import AdminIncidentTypesPage
from ..element.admin_streets import AdminStreetsPage
from ..element.queue import DispatchQueuePage
from ..element.queue_template import DispatchQueueTemplatePage
from ..element.incident import IncidentPage
from ..element.incident_template import IncidentTemplatePage
from ..element.report import IncidentReportPage
from ..element.report_template import IncidentReportTemplatePage
from ..element.root import RootPage
from .http import fixedETag, HeaderName, ContentType
from .klein import route
from .urls import URLs
from .auth import Authorization



class WebMixIn(object):
    """
    Mix-in for web interface.
    """

    #
    # Static content
    #

    @route(URLs.styleSheet.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def styleSheetResource(self, request):
        return self.styleSheet(request, "style.css")


    @route(URLs.logo.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def logoResource(self, request):
        request.setHeader(HeaderName.contentType.value, ContentType.PNG.value)
        return self.builtInResource(request, "logo.png")


    @route(URLs.imsJS.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def imsJSResource(self, request):
        return self.javaScript(request, "ims.js")


    #
    # Web interface
    #

    @route(u"/", methods=("HEAD", "GET"))
    def rootResource(self, request):
        """
        Server root page.

        This redirects to the application root page.
        """
        return self.redirect(request, URLs.prefix)


    @route(URLs.prefix.asText(), methods=("HEAD", "GET"))
    @route(URLs.prefix.asText() + u"/", methods=("HEAD", "GET"))
    @fixedETag
    def applicationRootResource(self, request):
        """
        Application root page.
        """
        return RootPage(self)


    @route(URLs.viewEvent.asText(), methods=("HEAD", "GET"))
    @route(URLs.viewEvent.asText() + u"/", methods=("HEAD", "GET"))
    def viewEventResource(self, request, event):
        """
        Event root page.

        This redirects to the event's dispatch queue page.
        """
        return self.redirect(request, URLs.viewDispatchQueueRelative)


    @route(URLs.admin.asText(), methods=("HEAD", "GET"))
    @route(URLs.admin.asText() + u"/", methods=("HEAD", "GET"))
    @fixedETag
    @inlineCallbacks
    def adminPage(self, request):
        # FIXME: Not strictly required because the underlying data is protected.
        # But the error you get is stupid, so let's avoid that for now.
        yield self.authorizeRequest(request, None, Authorization.imsAdmin)
        returnValue(AdminPage(self))


    @route(URLs.adminJS.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def adminJSResource(self, request):
        return self.javaScript(request, "admin.js")

    @route(URLs.adminAccessControl.asText(), methods=("HEAD", "GET"))
    @fixedETag
    @inlineCallbacks
    def adminAccessControlPage(self, request):
        # FIXME: Not strictly required because the underlying data is protected.
        # But the error you get is stupid, so let's avoid that for now.
        yield self.authorizeRequest(request, None, Authorization.imsAdmin)
        returnValue(AdminAccessControlPage(self))


    @route(URLs.adminAccessControlJS.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def adminAccessControlJSResource(self, request):
        return self.javaScript(request, "admin_acl.js")


    @route(URLs.adminIncidentTypes.asText(), methods=("HEAD", "GET"))
    @fixedETag
    @inlineCallbacks
    def adminAdminIncidentTypesPagePage(self, request):
        # FIXME: Not strictly required because the underlying data is protected.
        # But the error you get is stupid, so let's avoid that for now.
        yield self.authorizeRequest(request, None, Authorization.imsAdmin)
        returnValue(AdminIncidentTypesPage(self))


    @route(URLs.adminIncidentTypesJS.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def adminAdminIncidentTypesPageJSResource(self, request):
        return self.javaScript(request, "admin_types.js")


    @route(URLs.adminStreets.asText(), methods=("HEAD", "GET"))
    @fixedETag
    @inlineCallbacks
    def adminStreetsPage(self, request):
        # FIXME: Not strictly required because the underlying data is protected.
        # But the error you get is stupid, so let's avoid that for now.
        yield self.authorizeRequest(request, None, Authorization.imsAdmin)
        returnValue(AdminStreetsPage(self))


    @route(URLs.adminStreetsJS.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def adminStreetsJSResource(self, request):
        return self.javaScript(request, "admin_streets.js")


    @route(URLs.viewDispatchQueue.asText(), methods=("HEAD", "GET"))
    @fixedETag
    @inlineCallbacks
    def viewDispatchQueuePage(self, request, event):
        # FIXME: Not strictly required because the underlying data is protected.
        # But the error you get is stupid, so let's avoid that for now.
        yield self.authorizeRequest(request, event, Authorization.readIncidents)
        returnValue(DispatchQueuePage(self, event))


    @route(URLs.viewDispatchQueueTemplate.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def viewDispatchQueueTemplatePage(self, request):
        return DispatchQueueTemplatePage(self)


    @route(URLs.viewDispatchQueueJS.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def viewDispatchQueueJSResource(self, request):
        return self.javaScript(request, "queue.js")


    @route(URLs.viewIncidentNumber.asText(), methods=("HEAD", "GET"))
    @fixedETag
    @inlineCallbacks
    def viewIncidentPage(self, request, event, number):
        if number == u"new":
            authz = Authorization.readIncidents
            number = None
        else:
            authz = Authorization.writeIncidents
            try:
                number = int(number)
            except ValueError:
                returnValue(self.notFoundResource(request))

        yield self.authorizeRequest(request, event, authz)

        returnValue(IncidentPage(self, event, number))


    @route(URLs.viewIncidentNumberTemplate.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def viewIncidentNumberTemplatePage(self, request):
        return IncidentTemplatePage(self)


    @route(URLs.viewIncidentNumberJS.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def incidentJSResource(self, request):
        return self.javaScript(request, "incident.js")


    # FIXME: viewIncidentReports


    @route(URLs.viewIncidentReport.asText(), methods=("HEAD", "GET"))
    @fixedETag
    @inlineCallbacks
    def viewIncidentReportPage(self, request, number):
        if number == u"new":
            authz = Authorization.writeIncidentReports
            number = None
        else:
            authz = Authorization.readIncidentReports
            try:
                number = int(number)
            except ValueError:
                returnValue(self.notFoundResource(request))

        yield self.authorizeRequest(request, None, authz)

        returnValue(IncidentReportPage(self, number))


    @route(URLs.viewIncidentReportTemplate.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def viewIncidentReportTemplatePage(self, request):
        return IncidentReportTemplatePage(self)


    @route(URLs.viewIncidentReportJS.asText(), methods=("HEAD", "GET"))
    @fixedETag
    def viewIncidentReportJSResource(self, request):
        return self.javaScript(request, "report.js")
