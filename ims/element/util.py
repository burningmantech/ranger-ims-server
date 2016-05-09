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
Element utilities
"""

__all__ = [
    "normalize_priority",
]

# from datetime import timedelta as TimeDelta

# from twisted.logger import Logger
# from twisted.web.template import tags

# from ..tz import utcNow
# from ..data import (
#     IncidentState, IncidentType, Incident, ReportEntry,
#     Location, RodGarettAddress,
# )

# log = Logger()



# incident_types_to_ignore = set((IncidentType.Junk.value,))



# def ignore_incident(incident):
#     """
#     Determine whether to ignore an incident by default in reports.
#     """
#     if incident_types_to_ignore & set(incident.incident_types):
#         return True
#     return False


# def ignore_entry(entry):
#     """
#     Determine whether to ignore an incident entry by default in reports.
#     """
#     if entry.system_entry:
#         return True
#     return False


# def incidents_as_table(event, incidents, tz, caption=None, id=None):
#     attrs_activity = {"class": "incident_activity"}

#     if caption:
#         captionElement = tags.caption(caption, **attrs_activity)
#     else:
#         captionElement = ""

#     def incidents_as_rows(incidents):
#         attrs_incident = {"class": "incident"}
#         attrs_number = {"class": "incident_number"}
#         attrs_priority = {"class": "incident_priority"}
#         attrs_created = {"class": "incident_created"}
#         attrs_state = {"class": "incident_state"}
#         attrs_rangers = {"class": "incident_rangers"}
#         attrs_location = {"class": "incident_location"}
#         attrs_types = {"class": "incident_types"}
#         attrs_summary  = {"class": "incident_summary"}

#         yield tags.thead(
#             tags.tr(
#                 tags.th(u"#", **attrs_number),
#                 tags.th(u"Priority", **attrs_priority),
#                 tags.th(u"Created", **attrs_created),
#                 tags.th(u"State", **attrs_state),
#                 tags.th(u"Rangers", **attrs_rangers),
#                 tags.th(u"Location", **attrs_location),
#                 tags.th(u"Types", **attrs_types),
#                 tags.th(u"Summary", **attrs_summary),
#                 **attrs_incident
#             ),
#             **attrs_activity
#         )

#         def rows():
#             for incident in sorted(incidents):
#                 if incident.state is None:
#                     state = IncidentState.new
#                 else:
#                     state = incident.state

#                 if incident.priority is None:
#                     priority = 3
#                 else:
#                     priority = incident.priority

#                 if incident.rangers is None:
#                     rangers = []
#                 else:
#                     rangers = incident.rangers

#                 if incident.incident_types is None:
#                     incident_types = []
#                 else:
#                     incident_types = incident.incident_types

#                 try:
#                     yield tags.tr(
#                         tags.td(
#                             u"{0}".format(incident.number),
#                             **attrs_number
#                         ),
#                         tags.td(
#                             u"{0}".format(priority_name(priority)),
#                             **attrs_priority
#                         ),
#                         tags.td(
#                             u"{0}".format(formatTime(
#                                 incident.created, tz=tz, format=u"%d/%H:%M"
#                             )),
#                             **attrs_created
#                         ),
#                         tags.td(
#                             u"{0}".format(
#                                 IncidentState.describe(state)
#                             ),
#                             **attrs_state
#                         ),
#                         tags.td(
#                             u"{0}".format(
#                                 u", ".join(
#                                     ranger.handle
#                                     for ranger in rangers
#                                 )
#                             ),
#                             **attrs_rangers
#                         ),
#                         tags.td(
#                             u"{0}".format(
#                                 str(incident.location).decode("utf-8")
#                             ),
#                             **attrs_location
#                         ),
#                         tags.td(
#                             u"{0}".format(
#                                 u", ".join(incident_types)
#                             ),
#                             **attrs_types
#                         ),
#                         tags.td(
#                             u"{0}".format(incident.summaryFromReport()),
#                             **attrs_summary
#                         ),
#                         onclick=(
#                             u'window.open("/{0}/queue/incidents/{1}");'
#                             .format(event, incident.number)
#                         ),
#                         **attrs_incident
#                     )
#                 except Exception:
#                     log.failure(
#                         "Unable to render incident #{incident.number} "
#                         "in dispatch queue", incident=incident
#                     )
#                     yield tags.tr(
#                         tags.td(
#                             u"{0}".format(incident.number), **attrs_number
#                         ),
#                         tags.td(u"", **attrs_priority),
#                         tags.td(u"", **attrs_created),
#                         tags.td(u"", **attrs_state),
#                         tags.td(u"", **attrs_rangers),
#                         tags.td(u"", **attrs_location),
#                         tags.td(u"", **attrs_types),
#                         tags.td(u"", **attrs_summary),
#                         onclick=(
#                             u'window.open("/{0}/queue/incidents/{1}");'
#                             .format(event, incident.number)
#                         ),
#                         **attrs_incident
#                     )

#         yield tags.tbody(rows())

#     attrs_table = dict(attrs_activity)
#     if id is not None:
#         attrs_table[u"id"] = id

#     return tags.table(
#         captionElement,
#         incidents_as_rows(incidents),
#         **attrs_table
#     )


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


# def priority_name(priority):
#     """
#     Return a string label for a priority.
#     """
#     return {
#         1: u"High",
#         3: u"Normal",
#         5: u"Low",
#     }[normalize_priority(priority)]


# def formatTime(datetime, tz, format=u"%Y-%m-%d %H:%M:%S"):
#     if datetime is None:
#         return u""

#     datetime = datetime.astimezone(tz)
#     return datetime.strftime(format)
