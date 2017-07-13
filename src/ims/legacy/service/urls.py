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

__all__ = (
    "URLs",
)



@attrs(frozen=True)
class URLs(object):
    """
    Incident Management System URL schema.
    """

    root = URL.fromText("/")

    prefix = root.child("ims").child("")

    styleSheet = prefix.child("style.css")

    logo = prefix.child("logo.png")

    auth   = prefix.child("auth").child("")
    login  = auth.child("login")
    logout = auth.child("logout")

    jqueryBase = prefix.child("jquery").child("")
    jqueryJS   = jqueryBase.child("jquery.min.js")
    jqueryMap  = jqueryBase.child("jquery.min.map")

    bootstrapBase = prefix.child("bootstrap").child("")
    bootstrapCSS  = bootstrapBase.child("css", "bootstrap.min.css")
    bootstrapJS   = bootstrapBase.child("js", "bootstrap.min.js")

    dataTablesBase = prefix.child("datatables").child("")
    dataTablesJS = dataTablesBase.child(
        "media", "js", "jquery.dataTables.min.js"
    )
    dataTablesbootstrapCSS = dataTablesBase.child(
        "media", "css", "dataTables.bootstrap.min.css"
    )
    dataTablesbootstrapJS = dataTablesBase.child(
        "media", "js", "dataTables.bootstrap.min.js"
    )

    momentJS = prefix.child("moment.min.js")

    lscacheJS = prefix.child("lscache.min.js")

    # API endpoints
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

    # Web UI
    imsJS                      = prefix.child("ims.js")

    admin                      = prefix.child("admin").child("")
    adminJS                    = admin.child("admin.js")

    adminAccessControl         = admin.child("access")
    adminAccessControlJS       = admin.child("access.js")

    adminIncidentTypes         = admin.child("types")
    adminIncidentTypesJS       = admin.child("types.js")

    adminStreets               = admin.child("streets")
    adminStreetsJS             = admin.child("streets.js")

    viewEvents                 = prefix.child("events").child("")
    viewEvent                  = viewEvents.child("<eventID>").child("")

    viewDispatchQueue          = viewEvent.child("queue")
    viewDispatchQueueTemplate  = prefix.child("queue.html")
    viewDispatchQueueJS        = prefix.child("queue.js")
    viewDispatchQueueRelative  = URL.fromText("queue")

    viewIncidents              = viewEvent.child("incidents").child("")
    viewIncidentNumber         = viewIncidents.child("<number>")
    viewIncidentNumberTemplate = prefix.child("incident.html")
    viewIncidentNumberJS       = prefix.child("incident.js")

    viewIncidentReports        = prefix.child("incident_reports").child("")
    viewIncidentReport         = viewIncidentReports.child("<number>")
    viewIncidentReportTemplate = prefix.child("incident_report.html")
    viewIncidentReportJS       = prefix.child("incident_report.js")
