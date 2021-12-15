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
class URLs:
    """
    Incident Management System URL schema.
    """

    # Main application

    root: ClassVar = URL.fromText("/")

    prefix: ClassVar = root.child("ims").child("")
    urlsJS: ClassVar = prefix.child("urls.js")

    # API application

    api: ClassVar = prefix.child("api").child("")
    ping: ClassVar = api.child("ping").child("")
    bag: ClassVar = api.child("bag")
    auth: ClassVar = api.child("auth")
    acl: ClassVar = api.child("access")
    streets: ClassVar = api.child("streets")
    personnel: ClassVar = api.child("personnel").child("")
    incidentTypes: ClassVar = api.child("incident_types").child("")
    events: ClassVar = api.child("events").child("")
    event: ClassVar = events.child("<event_id>").child("")
    incidents: ClassVar = event.child("incidents").child("")
    incidentNumber: ClassVar = incidents.child("<incident_number>")
    incidentReports: ClassVar = event.child("incident_reports").child("")
    incidentReport: ClassVar = incidentReports.child("<incident_report_number>")

    eventSource: ClassVar = api.child("eventsource")
