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

    prefix = URL.fromText(u"/ims")

    styleSheet = prefix.child(u"style.css")

    logo = prefix.child(u"logo.png")

    login  = prefix.child(u"login")
    logout = prefix.child(u"logout")

    jqueryBase = prefix.child(u"jquery")
    jqueryJS   = jqueryBase.child(u"jquery.min.js")
    jqueryMap  = jqueryBase.child(u"jquery.min.map")

    bootstrapBase = prefix.child(u"bootstrap")
    bootstrapCSS  = bootstrapBase.child(u"css", u"bootstrap.min.css")
    bootstrapJS   = bootstrapBase.child(u"js", u"bootstrap.min.js")

    dataTablesBase = prefix.child(u"datatables")
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

    # API endpoints
    api              = prefix.child(u"api")
    ping             = api.child(u"ping")
    acl              = api.child(u"access")
    streets          = api.child(u"streets")
    personnel        = api.child(u"personnel")
    incidentTypes    = api.child(u"incident_types")
    events           = api.child(u"events")
    event            = events.child(u"<event>")
    locations        = event.child(u"locations")
    incidents        = event.child(u"incidents")
    incidentNumber   = incidents.child(u"<number>")

    # Web UI
    imsJS                      = prefix.child(u"ims.js")

    admin                      = prefix.child(u"admin")
    adminJS                    = admin.child(u"admin.js")

    adminAccessControl         = admin.child(u"access")
    adminAccessControlJS       = adminAccessControl.child(u"access.js")

    adminIncidentTypes         = admin.child(u"types")
    adminIncidentTypesJS       = adminAccessControl.child(u"types.js")

    adminStreets               = admin.child(u"streets")
    adminStreetsJS             = adminAccessControl.child(u"streets.js")

    viewEvents                 = prefix.child(u"events")
    viewEvent                  = viewEvents.child(u"<event>")

    viewDispatchQueue          = viewEvent.child(u"queue")
    viewDispatchQueueTemplate  = prefix.child(u"_queue.html")
    viewDispatchQueueJS        = prefix.child(u"queue.js")
    dispatchQueueData          = viewEvent.child(u"data")
    viewDispatchQueueRelative  = URL.fromText(u"queue")

    viewIncidents              = viewEvent.child(u"incidents")
    viewIncidentNumber         = viewIncidents.child(u"<number>")
    viewIncidentNumberTemplate = prefix.child(u"_incident.html")
    viewIncidentNumberJS       = prefix.child(u"incident.js")
