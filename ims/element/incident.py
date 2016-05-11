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
Incident element
"""

__all__ = [
    "IncidentPage",
]

from ..json import textFromJSON, incidentAsJSON
from ..data import concentricStreetNameByID
# from ..data import RodGarettAddress

from .base import Element, renderer



class IncidentPage(Element):
    """
    Incident element
    """

    def __init__(self, service, event, number):
        Element.__init__(
            self, u"incident", service,
            title=u"{} Incident #{}".format(event, number),
        )

        self.storage  = self.service.storage[event]
        self.event    = event
        self.incident = self.storage.readIncidentWithNumber(number)


    @renderer
    def root(self, request, tag):
        tag = Element.root(self, request, tag)

        slots = dict(
            incident_number=unicode(self.incident.number),
        )

        tag.fillSlots(**slots)

        return tag


    @renderer
    def incidentJSON(self, request, tag):
        return textFromJSON(incidentAsJSON(self.incident))


    @renderer
    def concentric_street_name_by_id(self, request, tag):
        return textFromJSON(concentricStreetNameByID[self.event])




    # @renderer
    # def incident_report_text(self, request, tag):
    #     attrs_entry_system = {"class": "incident_entry_system"}
    #     attrs_entry_user = {"class": "incident_entry_user"}
    #     attrs_timestamp = {"class": "incident_entry_timestamp"}
    #     attrs_entry_text = {"class": "incident_entry_text"}

    #     def entry_rendered(entry):
    #         if entry.system_entry:
    #             attrs_entry = attrs_entry_system
    #         else:
    #             attrs_entry = attrs_entry_user

    #         when = formatTime(entry.created, self.ims.config.TimeZone)

    #         author = entry.author
    #         if author is None:
    #             author = u"(unknown)"

    #         text = entry.text
    #         if text is None:
    #             text = u"(*** ERROR: no text? ***)"

    #         return tags.div(
    #             tags.span(
    #                 tags.time(when, datetime=when),
    #                 u", ",
    #                 author,
    #                 **attrs_timestamp
    #             ),
    #             ":",
    #             tags.br(),
    #             tags.span(
    #                 entry.text,
    #                 **attrs_entry_text
    #             ),
    #             **attrs_entry
    #         )

    #     def entries_rendered():
    #         for entry in self.incident.report_entries:
    #             yield entry_rendered(entry)

    #     return tag(*entries_rendered())
