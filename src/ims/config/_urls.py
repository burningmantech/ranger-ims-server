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
Incident Management System URL schema.
"""

from typing import ClassVar

from attrs import frozen
from hyperlink import URL


__all__ = ()


@frozen(kw_only=True)
class URLs:
    """
    Incident Management System URL schema.
    """

    # Main application

    root: ClassVar[URL] = URL.fromText("/")

    prefix: ClassVar[URL] = root.child("ims").child("")
    urlsJS: ClassVar[URL] = prefix.child("urls.js")

    # API application

    api: ClassVar[URL] = prefix.child("api").child("")
    ping: ClassVar[URL] = api.child("ping").child("")
    bag: ClassVar[URL] = api.child("bag")
    auth: ClassVar[URL] = api.child("auth")
    acl: ClassVar[URL] = api.child("access")
    streets: ClassVar[URL] = api.child("streets")
    personnel: ClassVar[URL] = api.child("personnel").child("")
    incidentTypes: ClassVar[URL] = api.child("incident_types").child("")
    events: ClassVar[URL] = api.child("events").child("")
    event: ClassVar[URL] = events.child("<event_id>").child("")
    incidents: ClassVar[URL] = event.child("incidents").child("")
    incidentNumber: ClassVar[URL] = incidents.child("<incident_number>")
    incident_reportEntries: ClassVar[URL] = incidentNumber.child("report_entries")
    incident_reportEntry: ClassVar[URL] = incident_reportEntries.child(
        "<report_entry_id>"
    )
    incidentAttachments: ClassVar[URL] = incidentNumber.child("attachments").child("")
    incidentAttachmentNumber: ClassVar[URL] = incidentAttachments.child(
        "<attachment_number>"
    )
    fieldReports: ClassVar[URL] = event.child("field_reports").child("")
    fieldReport: ClassVar[URL] = fieldReports.child("<field_report_number>")
    fieldReport_reportEntries: ClassVar[URL] = fieldReport.child("report_entries")
    fieldReport_reportEntry: ClassVar[URL] = fieldReport_reportEntries.child(
        "<report_entry_id>"
    )

    eventSource: ClassVar[URL] = api.child("eventsource")

    # Static resources
    static: ClassVar[URL] = prefix.child("static")
    styleSheet: ClassVar[URL] = static.child("style.css")
    logo: ClassVar[URL] = static.child("logo.png")

    # Auth application

    authApp: ClassVar[URL] = prefix.child("auth").child("")
    login: ClassVar[URL] = authApp.child("login")
    loginJS: ClassVar[URL] = static.child("login.js")
    logout: ClassVar[URL] = authApp.child("logout")

    # External application

    external: ClassVar[URL] = prefix.child("ext").child("")

    jqueryBase: ClassVar[URL] = external.child("jquery").child("")
    jqueryJS: ClassVar[URL] = jqueryBase.child("jquery.min.js")
    jqueryMap: ClassVar[URL] = jqueryBase.child("jquery.min.map")

    bootstrapBase: ClassVar[URL] = external.child("bootstrap").child("")
    bootstrapCSS: ClassVar[URL] = bootstrapBase.child("css", "bootstrap.min.css")
    bootstrapJS: ClassVar[URL] = bootstrapBase.child("js", "bootstrap.bundle.min.js")

    dataTablesBase: ClassVar[URL] = external.child("datatables").child("")
    dataTablesJS: ClassVar[URL] = dataTablesBase.child("js", "dataTables.min.js")
    dataTablesBootstrapCSS: ClassVar[URL] = dataTablesBase.child(
        "css", "dataTables.bootstrap5.min.css"
    )
    dataTablesBootstrapJS: ClassVar[URL] = dataTablesBase.child(
        "js", "dataTables.bootstrap5.min.js"
    )
    dataTablesResponsiveCSS: ClassVar[URL] = dataTablesBase.child(
        "css", "responsive.dataTables.min.css"
    )
    dataTablesResponsiveJS: ClassVar[URL] = dataTablesBase.child(
        "js", "dataTables.responsive.min.js"
    )

    # Web application

    app: ClassVar[URL] = prefix.child("app").child("")
    rootJS: ClassVar[URL] = static.child("root.js")

    imsJS: ClassVar[URL] = static.child("ims.js")

    themeJS: ClassVar[URL] = static.child("theme.js")

    admin: ClassVar[URL] = app.child("admin").child("")
    adminRootJS: ClassVar[URL] = static.child("admin_root.js")

    adminEvents: ClassVar[URL] = admin.child("events")
    adminEventsJS: ClassVar[URL] = static.child("admin_events.js")

    adminIncidentTypes: ClassVar[URL] = admin.child("types")
    adminIncidentTypesJS: ClassVar[URL] = static.child("admin_types.js")

    adminStreets: ClassVar[URL] = admin.child("streets")
    adminStreetsJS: ClassVar[URL] = static.child("admin_streets.js")

    viewEvents: ClassVar[URL] = app.child("events").child("")
    viewEvent: ClassVar[URL] = viewEvents.child("<event_id>").child("")

    viewIncidents: ClassVar[URL] = viewEvent.child("incidents").child("")
    viewIncidentsJS: ClassVar[URL] = static.child("incidents.js")
    viewIncidentsRelative: ClassVar[URL] = URL.fromText("incidents").child("")

    viewIncidentNumber: ClassVar[URL] = viewIncidents.child("<number>")
    viewIncidentJS: ClassVar[URL] = static.child("incident.js")

    viewFieldReports: ClassVar[URL] = viewEvent.child("field_reports").child("")
    viewFieldReportsJS: ClassVar[URL] = static.child("field_reports.js")
    viewFieldReportsRelative: ClassVar[URL] = URL.fromText("field_reports").child("")

    viewFieldReportNew: ClassVar[URL] = viewFieldReports.child("new")
    viewFieldReportNumber: ClassVar[URL] = viewFieldReports.child("<number>")
    viewFieldReportJS: ClassVar[URL] = static.child("field_report.js")
