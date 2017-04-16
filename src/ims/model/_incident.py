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
Incident
"""

from collections.abc import Iterable as IterableABC
from datetime import datetime as DateTime
from typing import Iterable

from ._entry import ReportEntry
from ._event import Event
from ._location import Location
from ._priority import IncidentPriority
from ._state import IncidentState
from ..ext.attr import attrib, attrs, instanceOf, optional


__all__ = ()



@attrs(frozen=True)
class Incident(object):
    """
    Incident
    """

    # FIXME: validator for IterableABC attrs

    event         = attrib(validator=instanceOf(Event))
    number        = attrib(validator=instanceOf(int))
    created       = attrib(validator=instanceOf(DateTime))
    state         = attrib(validator=instanceOf(IncidentState))
    priority      = attrib(validator=instanceOf(IncidentPriority))
    summary       = attrib(validator=optional(instanceOf(str)))
    rangers       = attrib(validator=instanceOf(IterableABC))
    incidentTypes = attrib(validator=instanceOf(IterableABC))
    location      = attrib(validator=instanceOf(Location))
    reportEntries = attrib(validator=instanceOf(IterableABC))


    def __str__(self) -> str:
        return (
            "{self.number}: {summary}".format(
                self=self,
                summary=self.summaryFromReport()
            )
        )


    def summaryFromReport(self) -> str:
        """
        Generate a summary by either using ``self.summary`` if it is not
        :obj:`None` or empty, or the first line of the first report entry.
        """
        return summaryFromReport(self.summary, self.reportEntries)



def summaryFromReport(
    summary: str, reportEntries: Iterable[ReportEntry]
) -> str:
    """
    Generate a summary by either using ``self.summary`` if it is not
    :obj:`None` or empty, or the first line of the first report entry.
    """
    if summary:
        return summary

    for entry in reportEntries:
        if not entry.automatic:
            return entry.text.split("\n")[0]

    return ""
