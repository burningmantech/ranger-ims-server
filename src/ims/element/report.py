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

from ..data.json import jsonTextFromObject
from ..service.auth import Authorization

from .base import Element, renderer


__all__ = (
    "IncidentReportPage",
)



class IncidentReportPage(Element):
    """
    Incident report page.
    """

    def __init__(self, service, number):
        Element.__init__(
            self, "report", service,
            title="Incident Report #{}".format(number),
        )

        self.number = number


    @renderer
    def editing_allowed(self, request, tag):
        if (request.authorizations & Authorization.writeIncidentReports):
            return jsonTextFromObject(True)
        else:
            return jsonTextFromObject(False)


    @renderer
    def incident_report_number(self, request, tag):
        return jsonTextFromObject(self.number)
