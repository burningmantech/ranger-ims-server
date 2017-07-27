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

from attr import attrs

from hyperlink import URL


__all__ = ()



@attrs(frozen=True)
class URLs(object):
    """
    Incident Management System URL schema.
    """

    # Main application

    root = URL.fromText("/")

    prefix = root.child("ims").child("")

    # Static resources
    static     = prefix.child("static")
    styleSheet = static.child("style.css")
    logo       = static.child("logo.png")

    # Auth application

    auth   = prefix.child("auth").child("")
    login  = auth.child("login")
    logout = auth.child("logout")

    # External application

    external = prefix.child("ext").child("")

    jqueryBase = external.child("jquery").child("")
    jqueryJS   = jqueryBase.child("jquery.min.js")
    jqueryMap  = jqueryBase.child("jquery.min.map")

    bootstrapBase = external.child("bootstrap").child("")
    bootstrapCSS  = bootstrapBase.child("css", "bootstrap.min.css")
    bootstrapJS   = bootstrapBase.child("js", "bootstrap.min.js")

    dataTablesBase = external.child("datatables").child("")
    dataTablesJS = dataTablesBase.child(
        "media", "js", "jquery.dataTables.min.js"
    )
    dataTablesBootstrapCSS = dataTablesBase.child(
        "media", "css", "dataTables.bootstrap.min.css"
    )
    dataTablesBootstrapJS = dataTablesBase.child(
        "media", "js", "dataTables.bootstrap.min.js"
    )

    momentJS = external.child("moment.min.js")

    lscacheJS = external.child("lscache.min.js")

    # API application

    api              = prefix.child("api").child("")
    ping             = api.child("ping").child("")
    acl              = api.child("access")
    streets          = api.child("streets")
    personnel        = api.child("personnel").child("")
    incidentTypes    = api.child("incident_types").child("")
    incidentReports  = api.child("incident_reports").child("")
    incidentReport   = incidentReports.child("<number>")
    events           = api.child("events").child("")
    event            = events.child("<eventID>").child("")
    locations        = event.child("locations").child("")
    incidents        = event.child("incidents").child("")
    incidentNumber   = incidents.child("<number>")

    eventSource      = api.child("eventsource")

    # Web application

    app                        = prefix.child("app").child("")

    imsJS                      = app.child("ims.js")

    admin                      = app.child("admin").child("")
    adminJS                    = admin.child("admin.js")

    adminAccessControl         = admin.child("access")
    adminAccessControlJS       = admin.child("access.js")

    adminIncidentTypes         = admin.child("types")
    adminIncidentTypesJS       = admin.child("types.js")

    adminStreets               = admin.child("streets")
    adminStreetsJS             = admin.child("streets.js")

    viewEvents                 = app.child("events").child("")
    viewEvent                  = viewEvents.child("<eventID>").child("")

    viewDispatchQueue          = viewEvent.child("queue")
    viewDispatchQueueTemplate  = app.child("queue.html")
    viewDispatchQueueJS        = app.child("queue.js")
    viewDispatchQueueRelative  = URL.fromText("queue")

    viewIncidents              = viewEvent.child("incidents").child("")
    viewIncidentNumber         = viewIncidents.child("<number>")
    viewIncidentNumberTemplate = app.child("incident.html")
    viewIncidentNumberJS       = app.child("incident.js")

    viewIncidentReports        = app.child("incident_reports").child("")
    viewIncidentReportsNew     = viewIncidentReports.child("new")
    viewIncidentReport         = viewIncidentReports.child("<number>")
    viewIncidentReportTemplate = app.child("incident_report.html")
    viewIncidentReportJS       = app.child("incident_report.js")
