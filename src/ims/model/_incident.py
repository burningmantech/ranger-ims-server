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

from collections.abc import Iterable, Sequence
from datetime import datetime as DateTime

from attrs import field, frozen

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


@frozen(kw_only=True, order=True)
class Incident(ReplaceMixIn):
    """
    Incident
    """

    eventID: str
    number: int
    created: DateTime = field(converter=normalizeDateTime)
    state: IncidentState
    priority: IncidentPriority
    summary: str | None
    location: Location
    rangerHandles: frozenset[str] = field(converter=freezeStrings)
    incidentTypes: frozenset[str] = field(converter=freezeStrings)
    reportEntries: Sequence[ReportEntry] = field(
        converter=sortAndFreezeReportEntries
    )
    incidentReportNumbers: frozenset[int] = field(converter=freezeIntegers)

    def __str__(self) -> str:
        return f"{self.eventID}#{self.number}: {self.summaryFromReport()}"

    def summaryFromReport(self) -> str:
        """
        Generate a summary by either using ``self.summary`` if it is not
        :obj:`None` or empty, or the first line of the first report entry.
        """
        return summaryFromReport(self.summary, self.reportEntries)


def summaryFromReport(
    summary: str | None, reportEntries: Iterable[ReportEntry]
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
