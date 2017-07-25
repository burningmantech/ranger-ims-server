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
Server root page.
"""

from ims.application import URLs

from .base import Element, renderer


__all__ = (
    "RootPage",
)



class RootPage(Element):
    """
    Server root page.
    """

    def __init__(self, service):
        """
        @param service: The service.
        """
        Element.__init__(
            self, "root", service,
            title="Ranger Incident Management System",
        )


    @renderer
    def new_incident_report(self, request, tag):
        """
        JSON string: add C{href} attribute to a tag with the URL to the new
        incident report page.
        """
        return tag(href=URLs.viewIncidentReports.child("new").asText())
