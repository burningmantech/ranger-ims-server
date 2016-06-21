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

    prefixURL = URL.fromText(u"/ims")

    styleSheetURL = prefixURL.child(u"style.css")

    logoURL = prefixURL.child(u"logo.png")

    loginURL  = prefixURL.child(u"login")
    logoutURL = prefixURL.child(u"logout")

    jqueryBaseURL = prefixURL.child(u"jquery")
    jqueryJSURL   = jqueryBaseURL.child(u"jquery.min.js")
    jqueryMapURL  = jqueryBaseURL.child(u"jquery.min.map")

    bootstrapBaseURL = prefixURL.child(u"bootstrap")
    bootstrapCSSURL  = bootstrapBaseURL.child(u"css", u"bootstrap.min.css")
    bootstrapJSURL   = bootstrapBaseURL.child(u"js", u"bootstrap.min.js")

    dataTablesBaseURL = prefixURL.child(u"datatables")
    dataTablesJSURL = dataTablesBaseURL.child(
        u"media", u"js", u"jquery.dataTables.min.js"
    )
    dataTablesBootstrapCSSURL = dataTablesBaseURL.child(
        u"media", u"css", u"dataTables.bootstrap.min.css"
    )
    dataTablesBootstrapJSURL = dataTablesBaseURL.child(
        u"media", u"js", u"dataTables.bootstrap.min.js"
    )

    momentJSURL = prefixURL.child(u"moment.min.js")

    imsJSURL      = prefixURL.child(u"ims.js")
    adminJSURL    = prefixURL.child(u"admin.js")
    queueJSURL    = prefixURL.child(u"queue.js")
    incidentJSURL = prefixURL.child(u"incident.js")

    # JSON endpoints
    adminURL            = prefixURL.child(u"admin")
    adminAccessURL      = adminURL.child(u"access")
    eventURL            = prefixURL.child(u"<event>")
    pingURL             = eventURL.child(u"ping")
    personnelURL        = eventURL.child(u"personnel")
    incidentTypesURL    = eventURL.child(u"incident_types")
    locationsURL        = eventURL.child(u"locations")
    incidentsURL        = eventURL.child(u"incidents")
    incidentNumberURL   = incidentsURL.child(u"<number>")

    # Web UI
    adminTemplateURL              = prefixURL.child(u"_admin")
    viewDispatchQueueURL          = eventURL.child(u"queue")
    viewDispatchQueueTemplateURL  = prefixURL.child(u"_queue")
    viewDispatchQueueJSURL        = viewDispatchQueueURL.child(u"queue.js")
    dispatchQueueDataURL          = viewDispatchQueueURL.child(u"data")
    viewDispatchQueueRelativeURL  = URL.fromText(u"queue")
    viewIncidentsURL              = viewDispatchQueueURL.child(u"incidents")
    viewIncidentNumberURL         = viewIncidentsURL.child(u"<number>")
    viewIncidentNumberTemplateURL = prefixURL.child(u"_incident")
