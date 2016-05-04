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
Dispatch queue page.
"""

__all__ = [
    "DispatchQueuePage",
]

from .base import Element, renderer

from ..json import JSON, textFromJSON
from ..data import concentricStreetNameByNumber

# from ..json import textFromJSON
# from ..service.query import (
#     incidentsFromQuery, showClosedFromQuery, termsFromQuery,
#     sinceDaysAgoFromQuery,
# )
# from .util import incidents_as_table



class DispatchQueuePage(Element):
    """
    Dispatch queue page.
    """

    columnNames = (
        u"#",
        u"Priority",
        u"Created",
        u"State",
        u"Rangers",
        u"Location",
        u"Types",
        u"Summary",
    )


    def __init__(self, service, storage, event):
        Element.__init__(
            self, u"queue", service,
            title=u"{} Dispatch Queue".format(event),
        )

        self.storage = storage
        self.event = event


    @renderer
    def table_headers(self, request, tag):
        return (
            tag.clone()(header)
            for header in self.columnNames
        )


    @renderer
    def data_url(self, request, tag):
        return (
            self.service.dispatchQueueDataURL.asText()
            .replace(u"<event>", unicode(self.event))
        )


    @renderer
    def incidents_url(self, request, tag):
        return (
            self.service.viewIncidentsURL.asText()
            .replace(u"<event>", unicode(self.event))
        )

    @renderer
    def columns(self, request, tag):
        return textFromJSON([
            {
                "data": JSON.incident_number.value,
                "className": "incident_number",
            },
            {
                "data": JSON.incident_priority.value,
                "className": "incident_priority",
                "searchable": False,
            },
            {
                "data": JSON.incident_created.value,
                "className": "incident_created",
            },
            {
                "data": JSON.incident_state.value,
                "className": "incident_state",
            },
            {
                "data": JSON.ranger_handles.value,
                "className": "incident_ranger_handles",
            },
            {
                "data": JSON.incident_location.value,
                "className": "incident_location",
            },
            {
                "data": JSON.incident_types.value,
                "className": "incident_types",
            },
            {
                "data": JSON.incident_summary.value,
                "className": "incident_summary",
            },
        ])


    @renderer
    def concentric_street_name_by_number(self, request, tag):
        return textFromJSON(concentricStreetNameByNumber[self.event])


    # @renderer
    # def data(self, request, tag):
    #     def format_date(d):
    #         if d is None:
    #             return ""
    #         else:
    #             return d.strftime("%a.%H:%M")

    #     storage = self.storage
    #     data = []

    #     for number, etag in incidentsFromQuery(storage, request):
    #         incident = storage.readIncidentWithNumber(number)

    #         if incident.summary:
    #             summary = incident.summary
    #         elif incident.report_entries:
    #             for entry in incident.report_entries:
    #                 if not entry.system_entry:
    #                     summary = entry.text
    #                     break
    #         else:
    #             summary = ""

    #         data.append([
    #             incident.number,
    #             incident.priority,
    #             format_date(incident.created),
    #             format_date(incident.dispatched),
    #             format_date(incident.on_scene),
    #             format_date(incident.closed),
    #             ", ".join(ranger.handle for ranger in incident.rangers),
    #             str(incident.location),
    #             ", ".join(incident.incident_types),
    #             summary,
    #         ])

    #     return textFromJSON(data)


    # @renderer
    # def queue(self, request, tag):
    #     storage = self.storage
    #     return tag(
    #         incidents_as_table(
    #             self.event,
    #             (
    #                 storage.readIncidentWithNumber(number)
    #                 for number, etag in incidentsFromQuery(storage, request)
    #             ),
    #             tz=self.ims.config.TimeZone,
    #             caption="Dispatch Queue",
    #             id="dispatch_queue",
    #         )
    #     )


    # @renderer
    # def hide_closed_column(self, request, tag):
    #     if showClosedFromQuery(request):
    #         return tag
    #     else:
    #         return "$('td:nth-child(6),th:nth-child(6)').hide();"


    # @renderer
    # def search_value(self, request, tag):
    #     terms = termsFromQuery(request)
    #     if terms:
    #         return tag(value=" ".join(terms))
    #     else:
    #         return tag


    # @renderer
    # def show_closed_value(self, request, tag):
    #     if showClosedFromQuery(request):
    #         return tag(value="true")
    #     else:
    #         return tag(value="false")


    # @renderer
    # def show_closed_checked(self, request, tag):
    #     if showClosedFromQuery(request):
    #         return tag(checked="")
    #     else:
    #         return tag


    # @renderer
    # def since_days_ago_value(self, request, tag):
    #     return tag(value=sinceDaysAgoFromQuery(request))


    # @renderer
    # def since_days_ago_selected(self, request, tag):
    #     if tag.attributes["value"] == sinceDaysAgoFromQuery(request):
    #         return tag(selected="")
    #     else:
    #         return tag
