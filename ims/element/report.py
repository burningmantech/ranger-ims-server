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
Incident report page.
"""

__all__ = [
    "IncidentReportPage",
]

from ..data.json import textFromJSON
from ..service.auth import Authorization
from ..service.urls import URLs

from .base import Element, renderer



class IncidentReportPage(Element):
    """
    Incident report page.
    """

    def __init__(self, service, number):
        Element.__init__(
            self, u"report", service,
            title=u"Incident Report #{}".format(number),
        )

        self.number = number


    @renderer
    def editing_allowed(self, request, tag):
        if (request.authorizations & Authorization.writeIncidentReports):
            return textFromJSON(True)
        else:
            return textFromJSON(False)


    @renderer
    def incident_report_number(self, request, tag):
        return textFromJSON(self.number)


    @renderer
    def template_url(self, request, tag):
        return textFromJSON(URLs.viewIncidentReportTemplate.asText())

    @renderer
    def incident_reports_url(self, request, tag):
        return textFromJSON(URLs.incidentReports.asText())


    @renderer
    def personnel_url(self, request, tag):
        return textFromJSON(URLs.personnel.asText())
