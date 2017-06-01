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
from typing import AbstractSet, Iterable, Optional, Sequence

from ._entry import ReportEntry
from ._event import Event
from ._location import Location
from ._priority import IncidentPriority
from ._state import IncidentState
from ..ext.attr import attrib, attrs, instanceOf, optional, sortedTuple

AbstractSet, Sequence  # silence linter


__all__ = ()



@attrs(frozen=True)
class Incident(object):
    """
    Incident
    """

    # FIXME: better validator for IterableABC attrs

    event = attrib(
        validator=instanceOf(Event)
    )  # type: Event
    number = attrib(
        validator=instanceOf(int)
    )  # type: int
    created = attrib(
        validator=instanceOf(DateTime)
    )  # type: DateTime
    state = attrib(
        validator=instanceOf(IncidentState)
    )  # type: IncidentState
    priority = attrib(
        validator=instanceOf(IncidentPriority)
    )  # type: IncidentPriority
    summary  = attrib(
        validator=optional(instanceOf(str))
    )  # type: Optional[str]
    location = attrib(
        validator=instanceOf(Location)
    )  # type: Location

    rangers = attrib(
        validator=instanceOf(IterableABC), convert=frozenset
    )  # type: AbstractSet
    incidentTypes = attrib(
        validator=instanceOf(IterableABC), convert=frozenset
    )  # type: AbstractSet
    reportEntries = attrib(
        validator=instanceOf(IterableABC), convert=sortedTuple
    )  # type: Sequence


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
    summary: Optional[str], reportEntries: Iterable[ReportEntry]
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
