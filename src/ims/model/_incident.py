# -*- test-case-name: ranger-ims-server.model.test.test_incident -*-

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

from datetime import datetime as DateTime
from typing import Iterable, Optional, Sequence

from attr import attrib, attrs

from ims.ext.attr import sorted_tuple

from ._convert import freezeIntegers, freezeStrings, normalizeDateTime
from ._entry import ReportEntry
from ._location import Location
from ._priority import IncidentPriority
from ._replace import ReplaceMixIn
from ._state import IncidentState


__all__ = ()


def sortAndFreezeReportEntries(
    reportEntries: Iterable[ReportEntry],
) -> Iterable[ReportEntry]:
    return sorted_tuple(reportEntries)


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class Incident(ReplaceMixIn):
    """
    Incident
    """

    eventID: str
    number: int
    created: DateTime = attrib(converter=normalizeDateTime)
    state: IncidentState
    priority: IncidentPriority
    summary: Optional[str]
    location: Location
    rangerHandles: frozenset[str] = attrib(converter=freezeStrings)
    incidentTypes: frozenset[str] = attrib(converter=freezeStrings)
    reportEntries: Sequence[ReportEntry] = attrib(
        converter=sortAndFreezeReportEntries
    )
    incidentReportNumbers: frozenset[int] = attrib(converter=freezeIntegers)

    def __str__(self) -> str:
        return f"{self.eventID}#{self.number}: {self.summaryFromReport()}"

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
