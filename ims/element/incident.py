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
Incident page.
"""

__all__ = [
    "IncidentPage",
]

from ..json import textFromJSON
from ..data import concentricStreetNameByID

from .base import Element, renderer



class IncidentPage(Element):
    """
    Incident page.
    """

    def __init__(self, service, event, number):
        Element.__init__(
            self, u"incident", service,
            title=u"{} Incident #{}".format(event, number),
        )

        self.event  = event
        self.number = number


    @renderer
    def root(self, request, tag):
        tag = Element.root(self, request, tag)

        slots = dict(
            incident_number=unicode(self.number),
        )

        tag.fillSlots(**slots)

        return tag


    @renderer
    def incident_number(self, request, tag):
        return unicode(self.number)


    @renderer
    def incidents_url(self, request, tag):
        return (
            self.service.incidentsURL.asText()
            .replace(u"<event>", unicode(self.event))
        )


    @renderer
    def personnel_url(self, request, tag):
        return (
            self.service.personnelURL.asText()
            .replace(u"<event>", unicode(self.event))
        )


    @renderer
    def concentric_street_name_by_id(self, request, tag):
        return textFromJSON(concentricStreetNameByID[self.event])
