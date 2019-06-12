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

from attr import attrs

from hyperlink import URL


__all__ = ()



@attrs(frozen=True, auto_attribs=True, kw_only=True)
class URLs(object):
    """
    Incident Management System URL schema.
    """

    # Main application

    root: ClassVar = URL.fromText("/")

    prefix: ClassVar = root.child("ims").child("")
    urlsJS: ClassVar = prefix.child("urls.js")

    # Static resources
    static: ClassVar     = prefix.child("static")
    styleSheet: ClassVar = static.child("style.css")
    logo: ClassVar       = static.child("logo.png")

    # Auth application

    auth: ClassVar   = prefix.child("auth").child("")
    login: ClassVar  = auth.child("login")
    logout: ClassVar = auth.child("logout")

    # External application

    external: ClassVar = prefix.child("ext").child("")

    jqueryBase: ClassVar = external.child("jquery").child("")
    jqueryJS: ClassVar   = jqueryBase.child("jquery.min.js")
    jqueryMap: ClassVar  = jqueryBase.child("jquery.min.map")

    bootstrapBase: ClassVar = external.child("bootstrap").child("")
    bootstrapCSS: ClassVar  = bootstrapBase.child("css", "bootstrap.min.css")
    bootstrapJS: ClassVar   = bootstrapBase.child("js", "bootstrap.min.js")

    dataTablesBase: ClassVar = external.child("datatables").child("")
    dataTablesJS: ClassVar = dataTablesBase.child(
        "media", "js", "jquery.dataTables.min.js"
    )
    dataTablesBootstrapCSS: ClassVar = dataTablesBase.child(
        "media", "css", "dataTables.bootstrap.min.css"
    )
    dataTablesBootstrapJS: ClassVar = dataTablesBase.child(
        "media", "js", "dataTables.bootstrap.min.js"
    )

    momentJS: ClassVar = external.child("moment.min.js")

    lscacheJS: ClassVar = external.child("lscache.min.js")

    # API application

    api: ClassVar              = prefix.child("api").child("")
    ping: ClassVar             = api.child("ping").child("")
    acl: ClassVar              = api.child("access")
    streets: ClassVar          = api.child("streets")
    personnel: ClassVar        = api.child("personnel").child("")
    incidentTypes: ClassVar    = api.child("incident_types").child("")
    events: ClassVar           = api.child("events").child("")
    event: ClassVar            = events.child("<eventID>").child("")
    locations: ClassVar        = event.child("locations").child("")
    incidents: ClassVar        = event.child("incidents").child("")
    incidentNumber: ClassVar   = incidents.child("<number>")
    incidentReports: ClassVar  = event.child("incident_reports").child("")
    incidentReport: ClassVar   = incidentReports.child("<number>")

    eventSource: ClassVar      = api.child("eventsource")

    # Web application

    app: ClassVar = prefix.child("app").child("")

    imsJS: ClassVar = static.child("ims.js")

    admin: ClassVar   = app.child("admin").child("")
    adminJS: ClassVar = static.child("admin.js")

    adminEvents: ClassVar   = admin.child("events")
    adminEventsJS: ClassVar = static.child("admin_events.js")

    adminIncidentTypes: ClassVar   = admin.child("types")
    adminIncidentTypesJS: ClassVar = static.child("admin_types.js")

    adminStreets: ClassVar   = admin.child("streets")
    adminStreetsJS: ClassVar = static.child("admin_streets.js")

    viewEvents: ClassVar = app.child("events").child("")
    viewEvent: ClassVar  = viewEvents.child("<eventID>").child("")

    viewDispatchQueue: ClassVar         = viewEvent.child("queue")
    viewDispatchQueueTemplate: ClassVar = app.child("queue.html")
    viewDispatchQueueJS: ClassVar       = static.child("queue.js")
    viewDispatchQueueRelative: ClassVar = URL.fromText("queue")

    viewIncidents: ClassVar = viewEvent.child("incidents").child("")

    viewIncidentNumber: ClassVar   = viewIncidents.child("<number>")
    viewIncidentTemplate: ClassVar = app.child("incident.html")
    viewIncidentJS: ClassVar       = static.child("incident.js")

    viewIncidentReports: ClassVar = (
        viewEvent.child("incident_reports").child("")
    )
    viewIncidentReportsTemplate: ClassVar = app.child("incident_reports.html")
    viewIncidentReportsJS: ClassVar = static.child("incident_reports.js")

    viewIncidentReportNew: ClassVar = viewIncidentReports.child("new")
    viewIncidentReportNumber: ClassVar = viewIncidentReports.child("<number>")
    viewIncidentReportTemplate: ClassVar = app.child("incident_report.html")
    viewIncidentReportJS: ClassVar = static.child("incident_report.js")
