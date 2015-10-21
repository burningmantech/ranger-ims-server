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
Shift Report Element
"""

__all__ = [
    "ShiftReportElement",
]

from twisted.python.constants import Names, NamedConstant
from twisted.web.template import renderer, tags

from ..dms import DirtShift
from ..data import Shift
from .base import BaseElement
from .util import ignore_incident, ignore_entry
from .util import num_shifts_from_query
from .util import incidents_as_table



class Activity(Names):
    created = NamedConstant()
    updated = NamedConstant()
    idle    = NamedConstant()
    closed  = NamedConstant()



class ShiftReportElement(BaseElement):
    def __init__(self, ims, template_name="report_shift"):
        BaseElement.__init__(self, ims, template_name, "Shift Summary")


    @property
    def incidents_by_shift(self):
        if not hasattr(self, "_incidents_by_shift"):
            storage = self.ims.storage
            incidents_by_shift = {}

            for number, etag in storage.listIncidents():
                incident = storage.readIncidentWithNumber(number)

                if ignore_incident(incident):
                    continue

                def add(datetime, activity):
                    if datetime is not None:
                        shift = Shift.from_datetime(DirtShift, datetime)
                        incidents_by_activity = incidents_by_shift.setdefault(
                            shift, {}
                        )
                        incidents_by_activity.setdefault(
                            activity, set()
                        ).add(incident)

                add(incident.created, Activity.created)
                add(incident.dispatched, Activity.updated)
                add(incident.on_scene, Activity.updated)
                add(incident.closed, Activity.closed)

                for entry in incident.report_entries:
                    if not ignore_entry(entry):
                        add(entry.created, Activity.updated)

            open_incidents = set()
            for shift in sorted(incidents_by_shift):
                incidents_by_activity = incidents_by_shift[shift]

                created_incidents = incidents_by_activity.get(
                    Activity.created, set()
                )

                open_incidents |= created_incidents
                open_incidents -= incidents_by_activity.get(
                    Activity.closed, set()
                )

                incidents_by_activity[Activity.idle] = (
                    open_incidents - created_incidents
                )

            self._incidents_by_shift = incidents_by_shift

        return self._incidents_by_shift


    @renderer
    def debug_activities(self, request, tag):
        output = []
        for shift in sorted(self.incidents_by_shift):
            output.append(u"{0}".format(shift))
            output.append(u"")
            incidents_by_activity = self.incidents_by_shift[shift]

            for activity in Activity.iterconstants():
                output.append(u"  {0}".format(activity))

                for incident in sorted(incidents_by_activity.get(
                    activity, set()
                )):
                    number = incident.number
                    summary = incident.summaryFromReport()
                    output.append(u"    {0}: {1}".format(number, summary))

                output.append(u"")

            output.append(u"")

        return tags.pre(u"\n".join(output))


    @renderer
    def report(self, request, tag):
        shift_elements = []
        max = int(num_shifts_from_query(request))
        count = 0

        for shift in sorted(self.incidents_by_shift, reverse=True):
            if max:
                count += 1
                if count > max:
                    break

            element = ShiftActivityElement(
                self.ims, shift, self.incidents_by_shift[shift]
            )
            shift_elements.append(element)

        return tag(shift_elements)


    @renderer
    def num_shifts_selected(self, request, tag):
        if tag.attributes["value"] == num_shifts_from_query(request):
            return tag(selected="")
        else:
            return tag



class ShiftActivityElement(BaseElement):
    def __init__(
        self, ims, shift, incidents_by_activity, template_name="shift"
    ):
        BaseElement.__init__(self, ims, template_name, str(shift))

        self.shift = shift
        self.incidents_by_activity = incidents_by_activity


    @renderer
    def shift_id(self, request, tag):
        return tag(id="shift:{0}".format(hash(self.shift)))


    @renderer
    def activity(self, request, tag):
        created = self.incidents_by_activity.get(Activity.created, set())
        updated = self.incidents_by_activity.get(Activity.updated, set())
        idle = self.incidents_by_activity.get(Activity.idle, set())
        closed  = self.incidents_by_activity.get(Activity.closed, set())

        def activity(caption, incidents):
            if incidents:
                return incidents_as_table(
                    incidents,
                    tz=self.ims.config.TimeZone,
                    caption=caption,
                    id="activity:{0}:{1}".format(
                        hash(self.shift), hash(caption)
                    ),
                )
            else:
                return ""

        return tag(
            activity("Created and open", created - closed),
            activity("Carried and updated", updated - created - closed),
            activity("Carried and idle", idle),
            activity("Carried and closed", closed - created),
            activity("Opened and closed", created & closed),
        )
