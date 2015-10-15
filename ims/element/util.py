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
Element Utilities
"""

__all__ = [
    "incident_types_to_ignore",
    "ignore_incident",
    "ignore_entry",
    "incidents_from_query",
    "terms_from_query",
    "show_closed_from_query",
    "since_days_ago_from_query",
    "since_from_query",
    "num_shifts_from_query",
    "query_value",
]

from datetime import timedelta as TimeDelta

from twisted.logger import Logger
from twisted.web.template import tags

from ..tz import utcNow
from ..data import (
    IncidentState, IncidentType, Incident, ReportEntry,
    Location, RodGarettAddress,
)

log = Logger()



incident_types_to_ignore = set((IncidentType.Junk.value,))



def ignore_incident(incident):
    if incident_types_to_ignore & set(incident.incident_types):
        return True
    return False


def ignore_entry(entry):
    if entry.system_entry:
        return True
    return False


def incidents_from_query(storage, request):
    if not hasattr(request, "ims_incidents"):
        if request.args:
            request.ims_incidents = storage.search_incidents(
                terms=terms_from_query(request),
                show_closed=show_closed_from_query(request),
                since=since_from_query(request),
            )
        else:
            request.ims_incidents = storage.list_incidents()

    return request.ims_incidents


def terms_from_query(request):
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


def show_closed_from_query(request):
    return query_value(request, "show_closed", "false", "true") == "true"


def since_days_ago_from_query(request):
    return query_value(request, "since_days_ago", "0")


def since_from_query(request):
    try:
        days = int(since_days_ago_from_query(request))
    except ValueError:
        days = 0

    if not days:
        return None

    return utcNow() - TimeDelta(days=days)


def num_shifts_from_query(request):
    return query_value(request, "num_shifts", "1")


def edits_from_query(author, number, request):
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


def query_value(request, key, default, no_args_default=None):
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


def incidents_as_table(event, incidents, tz, caption=None, id=None):
    attrs_activity = {"class": "incident_activity"}

    if caption:
        captionElement = tags.caption(caption, **attrs_activity)
    else:
        captionElement = ""

    def incidents_as_rows(incidents):
        attrs_incident = {"class": "incident"}
        attrs_number = {"class": "incident_number"}
        attrs_priority = {"class": "incident_priority"}
        attrs_created = {"class": "incident_created"}
        attrs_state = {"class": "incident_state"}
        attrs_rangers = {"class": "incident_rangers"}
        attrs_location = {"class": "incident_location"}
        attrs_types = {"class": "incident_types"}
        attrs_summary  = {"class": "incident_summary"}

        yield tags.thead(
            tags.tr(
                tags.th(u"#", **attrs_number),
                tags.th(u"Priority", **attrs_priority),
                tags.th(u"Created", **attrs_created),
                tags.th(u"State", **attrs_state),
                tags.th(u"Rangers", **attrs_rangers),
                tags.th(u"Location", **attrs_location),
                tags.th(u"Types", **attrs_types),
                tags.th(u"Summary", **attrs_summary),
                **attrs_incident
            ),
            **attrs_activity
        )

        def rows():
            for incident in sorted(incidents):
                if incident.state is None:
                    state = IncidentState.new
                else:
                    state = incident.state

                if incident.priority is None:
                    priority = 3
                else:
                    priority = incident.priority

                if incident.rangers is None:
                    rangers = []
                else:
                    rangers = incident.rangers

                if incident.incident_types is None:
                    incident_types = []
                else:
                    incident_types = incident.incident_types

                try:
                    yield tags.tr(
                        tags.td(
                            u"{0}".format(incident.number),
                            **attrs_number
                        ),
                        tags.td(
                            u"{0}".format(priority_name(priority)),
                            **attrs_priority
                        ),
                        tags.td(
                            u"{0}".format(formatTime(
                                incident.created, tz=tz, format=u"%d/%H:%M"
                            )),
                            **attrs_created
                        ),
                        tags.td(
                            u"{0}".format(
                                IncidentState.describe(state)
                            ),
                            **attrs_state
                        ),
                        tags.td(
                            u"{0}".format(
                                u", ".join(
                                    ranger.handle
                                    for ranger in rangers
                                )
                            ),
                            **attrs_rangers
                        ),
                        tags.td(
                            u"{0}".format(
                                str(incident.location).decode("utf-8")
                            ),
                            **attrs_location
                        ),
                        tags.td(
                            u"{0}".format(
                                u", ".join(incident_types)
                            ),
                            **attrs_types
                        ),
                        tags.td(
                            u"{0}".format(incident.summaryFromReport()),
                            **attrs_summary
                        ),
                        onclick=(
                            u'window.open("/{0}/queue/incidents/{1}");'
                            .format(event, incident.number)
                        ),
                        **attrs_incident
                    )
                except Exception:
                    log.failure(
                        "Unable to render incident #{incident.number} "
                        "in dispatch queue", incident=incident
                    )
                    yield tags.tr(
                        tags.td(
                            u"{0}".format(incident.number), **attrs_number
                        ),
                        tags.td(u"", **attrs_priority),
                        tags.td(u"", **attrs_created),
                        tags.td(u"", **attrs_state),
                        tags.td(u"", **attrs_rangers),
                        tags.td(u"", **attrs_location),
                        tags.td(u"", **attrs_types),
                        tags.td(u"", **attrs_summary),
                        onclick=(
                            u'window.open("/{0}/queue/incidents/{1}");'
                            .format(event, incident.number)
                        ),
                        **attrs_incident
                    )

        yield tags.tbody(rows())

    attrs_table = dict(attrs_activity)
    if id is not None:
        attrs_table[u"id"] = id

    return tags.table(
        captionElement,
        incidents_as_rows(incidents),
        **attrs_table
    )


def normalize_priority(priority):
    """
    Normalize priority 1, 2, 3, 4 or 5 to 1, 3 or 5.
    """
    return {
        1: 1,
        2: 1,
        3: 3,
        4: 5,
        5: 5,
    }[priority]


def priority_name(priority):
    """
    Return a string label for a priority.
    """
    return {
        1: u"High",
        3: u"Normal",
        5: u"Low",
    }[normalize_priority(priority)]


def formatTime(datetime, tz, format=u"%Y-%m-%d %H:%M:%S"):
    if datetime is None:
        return u""

    datetime = datetime.astimezone(tz)
    return datetime.strftime(format)
