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
Incident Element
"""

__all__ = [
    "IncidentElement",
]

from twisted.web.template import renderer, tags

from .base import BaseElement
from ..json import datetime_as_rfc3339



class IncidentElement(BaseElement):
    def __init__(self, ims, number):
        BaseElement.__init__(
            self, ims, "incident",
            "Incident #{0}".format(number)
        )
        self.incident = self.ims.storage.read_incident_with_number(number)

        for attr_name in (
            "number",
            "priority",
            "created",
            "dispatched",
            "on_scene",
            "closed",
            "summary",
        ):
            @renderer
            def render_attr(request, tag, attr_name=attr_name):
                return tag(u"{0}".format(getattr(self.incident, attr_name)))

            setattr(self, attr_name, render_attr)


    @renderer
    def state_selected(self, request, tag):
        for state, name in (
            (self.incident.closed, "closed"),
            (self.incident.on_scene, "on_scene"),
            (self.incident.dispatched, "dispatched"),
            (self.incident.created, "created"),
        ):
            if state:
                if tag.attributes["value"] == name:
                    return tag(selected="")
                else:
                    return tag


    @renderer
    def priority_selected(self, request, tag):
        if int(tag.attributes["value"]) == self.incident.priority:
            return tag(selected="")
        else:
            return tag


    @renderer
    def summary_value(self, request, tag):
        return tag(value=u"{0}".format(self.incident.summary))


    @renderer
    def rangers_options(self, request, tag):
        return tag(
            tags.option(
                u"{ranger.handle} ({ranger.name})".format(ranger=ranger),
                value=ranger.handle
            )
            for ranger in self.incident.rangers
        )


    @renderer
    def types_options(self, request, tag):
        return tag(
            tags.option(
                type,
                value=type
            )
            for type in self.incident.incident_types
        )


    @renderer
    def location_name_value(self, request, tag):
        if (
            self.incident.location is None or
            self.incident.location.name is None
        ):
            return tag(value=u"")

        return tag(value=u"{0}".format(self.incident.location.name))


    @renderer
    def location_address_value(self, request, tag):
        if (
            self.incident.location is None or
            self.incident.location.address is None
        ):
            return tag(value=u"")

        return tag(value=u"{0}".format(self.incident.location.address))


    @renderer
    def incident_report(self, request, tag):
        attrs_entry_system = {"class": "incident_entry_system"}
        attrs_entry_user = {"class": "incident_entry_user"}
        attrs_timestamp = {"class": "incident_entry_timestamp"}
        attrs_entry_text = {"class": "incident_entry_text"}

        def entry_rendered(entry):
            if entry.system_entry:
                attrs_entry = attrs_entry_system
            else:
                attrs_entry = attrs_entry_user

            when = datetime_as_rfc3339(entry.created)

            return tags.div(
                tags.span(
                    tags.time(when, datetime=when),
                    u", ",
                    entry.author,
                    **attrs_timestamp
                ),
                ":",
                tags.br(),
                tags.span(
                    entry.text,
                    **attrs_entry_text
                ),
                **attrs_entry
            )

        def entries_rendered():
            for entry in self.incident.report_entries:
                yield entry_rendered(entry)

        return tag(*entries_rendered())
