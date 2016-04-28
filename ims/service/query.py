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
    "incidentsFromQuery",
    "termsFromQuery",
    "showClosedFromQuery",
    "sinceDaysAgoFromQuery",
    "sinceFromQuery",
    "numShiftsFromQuery",
    "editsFromQuery",
    "queryValue",
]

from datetime import timedelta as TimeDelta

from ..tz import utcNow
from ..data import (
    IncidentState, Incident, ReportEntry, Location, RodGarettAddress
)



def incidentsFromQuery(storage, request):
    """
    Find incidents matching a request query.
    """
    if not hasattr(request, "ims_incidents"):
        if request.args:
            request.ims_incidents = storage.searchIncidents(
                terms=termsFromQuery(request),
                showClosed=showClosedFromQuery(request),
                since=sinceFromQuery(request),
            )
        else:
            request.ims_incidents = storage.listIncidents()

    return request.ims_incidents


def termsFromQuery(request):
    """
    Compute query terms from a request.
    """
    if not hasattr(request, "ims_terms"):
        if request.args:
            terms = set()

            for query in request.args.get("search", []):
                for term in query.split(" "):
                    terms.add(term)

            for term in request.args.get("term", []):
                terms.add(term)

            request.ims_terms = terms

        else:
            request.ims_terms = set()

    return request.ims_terms


def showClosedFromQuery(request):
    """
    Determine whether a request query indicates that we should display closed
    incidents.
    """
    return queryValue(request, "show_closed", "false", "true") == "true"


def sinceDaysAgoFromQuery(request):
    """
    Determine how many days back a request query indicates that we should
    display incidents for.
    """
    return queryValue(request, "since_days_ago", "0")


def sinceFromQuery(request):
    """
    Determine what start time a request query indicates that we should display
    incidents for.
    """
    try:
        days = int(sinceDaysAgoFromQuery(request))
    except ValueError:
        days = 0

    if not days:
        return None

    return utcNow() - TimeDelta(days=days)


def numShiftsFromQuery(request):
    """
    Determine the number of shifts a request query indicates that we should
    display incidents for.
    """
    return queryValue(request, "num_shifts", "1")


def editsFromQuery(author, number, request):
    if not request.args:
        return None

    priority = summary = location = address = rangers = None
    incident_types = report_entries = state = None

    def get(key, cast, defaultArgs=[]):
        for value in request.args.get(key, defaultArgs):
            return cast(value)
        return None

    def radialHourMinute(radial):
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
    state = get("state", IncidentState.lookupByName)
    summary = get("summary", unicode)

    location_name = get("location_name", unicode)
    location_hour, location_minute = get(
        "location_radial", radialHourMinute, [""]
    )
    location_concentric = get("location_concentric", concentric)
    location_description = get("location_description", unicode)

    if (
        location_hour is not None or
        location_minute is not None or
        location_concentric is not None or
        location_description is not None
    ):
        address = RodGarettAddress(
            radialHour=location_hour,
            radialMinute=location_minute,
            concentric=location_concentric,
            description=location_description,
        )

    location = Location(name=location_name, address=address)

    # FIXME:
    rangers

    # FIXME:
    incident_types

    report_entries = []

    for text in request.args.get("report_text", []):
        report_entries = (
            ReportEntry(
                author=author,
                text=text.replace("\r\n", "\n").decode("utf-8"),
            ),
        )

    return Incident(
        number,
        priority=priority,
        summary=summary,
        location=location,
        rangers=rangers,
        incident_types=incident_types,
        report_entries=report_entries,
        state=state,
    )


def queryValue(request, key, default, no_args_default=None):
    """
    Determine the value for a query argument from a request.
    """
    attr_name = "ims_qv_{0}".format(key)

    if not hasattr(request, attr_name):
        if request.args:
            try:
                setattr(
                    request,
                    attr_name,
                    request.args.get(key, [default])[-1]
                )
            except IndexError:
                setattr(request, attr_name, default)
        else:
            if no_args_default is not None:
                setattr(request, attr_name, no_args_default)
            else:
                setattr(request, attr_name, default)

    return getattr(request, attr_name)
