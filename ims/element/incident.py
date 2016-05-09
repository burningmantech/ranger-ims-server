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

from .base import Element, renderer

from .util import normalize_priority  # formatTime

# from ..data import RodGarettAddress



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


    # def apply_disabled(self, attrs):
    #     if not self.edit_enabled:
    #         attrs["disabled"] = u"disabled"


    # @renderer
    # def editable(self, request, tag):
    #     if self.edit_enabled:
    #         return tag
    #     else:
    #         return u""


    @renderer
    def state_option(self, request, tag):
        if tag.attributes["value"] == self.incident.state.name:
            return tag(selected="")
        else:
            return tag


    @renderer
    def priority_option(self, request, tag):
        priority = normalize_priority(self.incident.priority)

        if int(tag.attributes["value"]) == priority:
            return tag(selected="")
        else:
            return tag


    # @renderer
    # def incident_summary_input(self, request, tag):
    #     attrs = dict(value=u"{0}".format(self.incident.summary))
    #     self.apply_disabled(attrs)
    #     return tag(**attrs)


    # @renderer
    # def ranger_row(self, request, tag):
    #     if self.incident.rangers is None:
    #         return

    #     for ranger in self.incident.rangers:
    #         yield tag.clone().fillSlots(ranger=ranger.handle)


    # @renderer
    # def incident_type_row(self, request, tag):
    #     if self.incident.incident_types is None:
    #         return

    #     for incident_type in self.incident.incident_types:
    #         yield tag.clone().fillSlots(incident_type=incident_type)


    # @renderer
    # def location_name_input(self, request, tag):
    #     attrs = dict()
    #     self.apply_disabled(attrs)

    #     if (
    #         self.incident.location is None or
    #         self.incident.location.name is None
    #     ):
    #         attrs["value"] = u""
    #     else:
    #         attrs["value"] = u"{0}".format(self.incident.location.name)

    #     return tag(**attrs)


    # @renderer
    # def location_radial_input(self, request, tag):
    #     attrs = dict()
    #     self.apply_disabled(attrs)

    #     location = self.incident.location

    #     attrs["value"] = u""

    #     if location is not None:
    #         address = location.address

    #         if address is not None:
    #             if isinstance(address, RodGarettAddress):
    #                 hour   = address.radialHour
    #                 minute = address.radialMinute

    #                 if hour is not None or minute is not None:
    #                     if hour is None:
    #                         hour = u""
    #                     else:
    #                         hour = u"{:d}".format(hour)

    #                     if minute is None:
    #                         minute = u""
    #                     else:
    #                         minute = u"{:02d}".format(minute)

    #                     attrs["value"] = u"{}:{}".format(hour, minute)

    #     return tag(**attrs)


    # @renderer
    # def location_concentric_option(self, request, tag):
    #     attrs = dict()
    #     self.apply_disabled(attrs)

    #     location = self.incident.location

    #     if location is not None:
    #         address = location.address

    #         if address is not None:
    #             if isinstance(address, RodGarettAddress):
    #                 concentric = address.concentric

    #                 if tag.attributes["value"] == concentric:
    #                     attrs["selected"] = u""

    #     return tag(**attrs)


    # @renderer
    # def location_description_input(self, request, tag):
    #     attrs = dict()
    #     self.apply_disabled(attrs)

    #     location = self.incident.location

    #     attrs["value"] = u""

    #     if location is not None:
    #         address = location.address

    #         if address is not None:
    #             if address.description is not None:
    #                 attrs["value"] = address.description

    #     return tag(**attrs)


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

    # @renderer
    # def incident_report_textarea(self, request, tag):
    #     if self.edit_enabled:
    #         return tag
    #     else:
    #         return u""
