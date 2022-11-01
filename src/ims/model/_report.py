# -*- test-case-name: ranger-ims-server.model.test.test_report -*-

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
Incident Report
"""

from collections.abc import Sequence
from datetime import datetime as DateTime

from attr import attrib, attrs

from ._convert import normalizeDateTime
from ._entry import ReportEntry
from ._incident import sortAndFreezeReportEntries, summaryFromReport
from ._replace import ReplaceMixIn


__all__ = ()


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class IncidentReport(ReplaceMixIn):
    """
    Incident
    """

    eventID: str
    number: int
    created: DateTime = attrib(converter=normalizeDateTime)
    summary: str | None
    incidentNumber: int | None
    reportEntries: Sequence[ReportEntry] = attrib(
        converter=sortAndFreezeReportEntries
    )

    def __str__(self) -> str:
        return f"{self.eventID}#{self.number}: {self.summaryFromReport()}"

    def summaryFromReport(self) -> str:
        """
        Generate a summary by either using ``self.summary`` if it is not
        :obj:`None` or empty, or the first line of the first report entry.
        """
        return summaryFromReport(self.summary, self.reportEntries)
