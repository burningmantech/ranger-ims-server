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
URL query.
"""

__all__ = [
    "applyEditsFromQuery",
]

from ..data.model import IncidentState, ReportEntry
from ..store.istore import NoSuchIncidentError



def applyEditsFromQuery(storage, event, number, author, request):
    """
    Create an incident object that contains changes to apply to an existing
    incident; all of its properties represent updates to apply.
    """
    try:
        number = int(number)
    except ValueError:
        raise NoSuchIncidentError(number)

    if not request.args:
        return None

    def get(key, cast, defaultArgs=[]):
        for value in request.args.get(key, defaultArgs):
            return cast(value)
        return None

    def radialHourAndMinute(radial):
        if radial:
            try:
                hour, minute = radial.split(":")
            except ValueError:
                return (None, None)
            return (int(hour), int(minute))
        else:
            return (None, None)

    def concentric(n):
        if n:
            return int(n)
        else:
            return None

    priority = get("priority", int)
    if priority is not None:
        storage.setIncidentPriority(event, number, priority)

    state = get("state", IncidentState.lookupByName)
    if state is not None:
        storage.setIncidentState(event, number, state)

    summary = get("summary", unicode)
    if summary is not None:
        storage.setIncidentSummary(event, number, summary)

    locationName = get("location_name", unicode)
    if locationName is not None:
        storage.setIncidentLocationName(event, number, locationName)

    streetID = get("location_concentric", unicode)
    if streetID is not None:
        if streetID == "":  # unset this, please
            streetID = None
        storage.setIncidentLocationConcentricStreet(event, number, streetID)

    hour, minute = get(
        "location_radial", radialHourAndMinute, [""]
    )
    if hour is not None:
        storage.setIncidentLocationRadialHour(event, number, hour)
    if minute is not None:
        storage.setIncidentLocationRadialMinute(event, number, minute)

    hour = get("location_radial_hour", int)
    if hour is not None:
        storage.setIncidentLocationRadialHour(event, number, hour)

    minute = get("location_radial_minute", int)
    if minute is not None:
        storage.setIncidentLocationRadialMinute(event, number, minute)

    description = get("location_description", unicode)
    if description is not None:
        storage.setIncidentLocationDescription(event, number, description)

    # FIXME: rangers
    # FIXME: incidentTypes

    for text in request.args.get("report_text", []):
        reportEntry = ReportEntry(
            author=author,
            text=text.replace("\r\n", "\n").decode("utf-8"),
        )
        storage.addIncidentReportEntry(event, number, reportEntry)
