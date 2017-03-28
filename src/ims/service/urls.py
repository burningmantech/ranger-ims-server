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

__all__ = [
    "URLs",
]

from twisted.python.url import URL



class URLs(object):
    """
    Incident Management System URL schema.
    """

    root = URL.fromText(u"/")

    prefix = URL.fromText(u"/ims/")

    styleSheet = prefix.child(u"style.css")

    logo = prefix.child(u"logo.png")

    login  = prefix.child(u"login")
    logout = prefix.child(u"logout")

    jqueryBase = prefix.child(u"jquery").child(u"")
    jqueryJS   = jqueryBase.child(u"jquery.min.js")
    jqueryMap  = jqueryBase.child(u"jquery.min.map")

    bootstrapBase = prefix.child(u"bootstrap").child(u"")
    bootstrapCSS  = bootstrapBase.child(u"css", u"bootstrap.min.css")
    bootstrapJS   = bootstrapBase.child(u"js", u"bootstrap.min.js")

    dataTablesBase = prefix.child(u"datatables").child(u"")
    dataTablesJS = dataTablesBase.child(
        u"media", u"js", u"jquery.dataTables.min.js"
    )
    dataTablesbootstrapCSS = dataTablesBase.child(
        u"media", u"css", u"dataTables.bootstrap.min.css"
    )
    dataTablesbootstrapJS = dataTablesBase.child(
        u"media", u"js", u"dataTables.bootstrap.min.js"
    )

    momentJS = prefix.child(u"moment.min.js")

    lscacheJS = prefix.child(u"lscache.min.js")

    # API endpoints
    api              = prefix.child(u"api").child(u"")
    ping             = api.child(u"ping").child(u"")
    acl              = api.child(u"access")
    streets          = api.child(u"streets")
    personnel        = api.child(u"personnel").child(u"")
    incidentTypes    = api.child(u"incident_types").child(u"")
    incidentReports  = api.child(u"incident_reports").child(u"")
    incidentReport   = incidentReports.child(u"<number>")
    events           = api.child(u"events").child(u"")
    event            = events.child(u"<eventID>").child(u"")
    locations        = event.child(u"locations").child(u"")
    incidents        = event.child(u"incidents").child(u"")
    incidentNumber   = incidents.child(u"<number>")

    eventSource      = api.child(u"eventsource")

    # Web UI
    imsJS                      = prefix.child(u"ims.js")

    admin                      = prefix.child(u"admin").child(u"")
    adminJS                    = admin.child(u"admin.js")

    adminAccessControl         = admin.child(u"access")
    adminAccessControlJS       = admin.child(u"access.js")

    adminIncidentTypes         = admin.child(u"types")
    adminIncidentTypesJS       = admin.child(u"types.js")

    adminStreets               = admin.child(u"streets")
    adminStreetsJS             = admin.child(u"streets.js")

    viewEvents                 = prefix.child(u"events").child(u"")
    viewEvent                  = viewEvents.child(u"<eventID>").child(u"")

    viewDispatchQueue          = viewEvent.child(u"queue")
    viewDispatchQueueTemplate  = prefix.child(u"queue.html")
    viewDispatchQueueJS        = prefix.child(u"queue.js")
    viewDispatchQueueRelative  = URL.fromText(u"queue")

    viewIncidents              = viewEvent.child(u"incidents").child(u"")
    viewIncidentNumber         = viewIncidents.child(u"<number>")
    viewIncidentNumberTemplate = prefix.child(u"incident.html")
    viewIncidentNumberJS       = prefix.child(u"incident.js")

    viewIncidentReports        = prefix.child(u"incident_reports").child(u"")
    viewIncidentReport         = viewIncidentReports.child(u"<number>")
    viewIncidentReportTemplate = prefix.child(u"incident_report.html")
    viewIncidentReportJS       = prefix.child(u"incident_report.js")
