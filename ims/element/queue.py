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
Dispatch Queue Element
"""

__all__ = [
    "DispatchQueueElement",
]

from twisted.web.template import renderer

from ..json import json_as_text
from .base import BaseElement
from .util import incidents_from_query
from .util import show_closed_from_query
from .util import terms_from_query
from .util import since_days_ago_from_query
from .util import incidents_as_table



class DispatchQueueElement(BaseElement):
    def __init__(self, ims):
        BaseElement.__init__(self, ims, "queue", "Dispatch Queue")


    @renderer
    def user(self, request, tag):
        return tag(self.ims.user)


    @renderer
    def data(self, request, tag):
        def format_date(d):
            if d is None:
                return ""
            else:
                return d.strftime("%a.%H:%M")

        data = []

        for number, etag in incidents_from_query(self.ims, request):
            incident = self.ims.storage.read_incident_with_number(number)

            if incident.summary:
                summary = incident.summary
            elif incident.report_entries:
                for entry in incident.report_entries:
                    if not entry.system_entry:
                        summary = entry.text
                        break
            else:
                summary = ""

            data.append([
                incident.number,
                incident.priority,
                format_date(incident.created),
                format_date(incident.dispatched),
                format_date(incident.on_scene),
                format_date(incident.closed),
                ", ".join(ranger.handle for ranger in incident.rangers),
                str(incident.location),
                ", ".join(incident.incident_types),
                summary,
            ])

        return json_as_text(data)


    @renderer
    def queue(self, request, tag):
        return tag(incidents_as_table(
            (
                self.ims.storage.read_incident_with_number(number)
                for number, etag in incidents_from_query(self.ims, request)
            ),
            caption="Dispatch Queue",
            id="dispatch_queue",
        ))


    @renderer
    def hide_closed_column(self, request, tag):
        if show_closed_from_query(request):
            return tag
        else:
            return "$('td:nth-child(6),th:nth-child(6)').hide();"


    @renderer
    def search_value(self, request, tag):
        terms = terms_from_query(request)
        if terms:
            return tag(value=" ".join(terms))
        else:
            return tag


    @renderer
    def show_closed_value(self, request, tag):
        if show_closed_from_query(request):
            return tag(value="true")
        else:
            return tag(value="false")


    @renderer
    def show_closed_checked(self, request, tag):
        if show_closed_from_query(request):
            return tag(checked="")
        else:
            return tag


    @renderer
    def since_days_ago_value(self, request, tag):
        return tag(value=since_days_ago_from_query(request))


    @renderer
    def since_days_ago_selected(self, request, tag):
        if tag.attributes["value"] == since_days_ago_from_query(request):
            return tag(selected="")
        else:
            return tag
