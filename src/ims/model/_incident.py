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
from typing import AbstractSet, Any, Iterable, Optional, Sequence, TypeVar

from attr import asdict, attrib, attrs
from attr.validators import instance_of, optional

from ims.ext.attr import sorted_tuple

from ._entry import ReportEntry
from ._event import Event
from ._location import Location
from ._priority import IncidentPriority
from ._state import IncidentState

AbstractSet, Sequence  # silence linter


__all__ = ()


TIncident = TypeVar("TIncident", bound="Incident")



@attrs(frozen=True)
class Incident(object):
    """
    Incident
    """

    # FIXME: better validator for IterableABC attrs

    event = attrib(
        validator=instance_of(Event)
    )  # type: Event
    number = attrib(
        validator=instance_of(int)
    )  # type: int
    created = attrib(
        validator=instance_of(DateTime)
    )  # type: DateTime
    state = attrib(
        validator=instance_of(IncidentState)
    )  # type: IncidentState
    priority = attrib(
        validator=instance_of(IncidentPriority)
    )  # type: IncidentPriority
    summary  = attrib(
        validator=optional(instance_of(str))
    )  # type: Optional[str]
    location = attrib(
        validator=instance_of(Location)
    )  # type: Location

    rangerHandles = attrib(
        validator=instance_of(IterableABC), convert=frozenset
    )  # type: AbstractSet[str]
    incidentTypes = attrib(
        validator=instance_of(IterableABC), convert=frozenset
    )  # type: AbstractSet[str]
    reportEntries = attrib(
        validator=instance_of(IterableABC), convert=sorted_tuple
    )  # type: Sequence[ReportEntry]


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


    def replace(self: TIncident, **kwargs: Any) -> TIncident:
        """
        Return a new incident with the same values, except those specified by
        keyword arguments.
        """
        newArgs = asdict(self, recurse=False)
        newArgs.update(kwargs)
        return self.__class__(**newArgs)



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
