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

from collections.abc import Iterable
from datetime import datetime as DateTime
from typing import Optional, Sequence

from ._incident import summaryFromReport
from ..ext.attr import attrib, attrs, instanceOf, optional, sortedTuple

Optional, Sequence  # Silence linter


__all__ = ()



@attrs(frozen=True)
class IncidentReport(object):
    """
    Incident
    """

    # FIXME: better validator for reportEntries

    number = attrib(
        validator=instanceOf(int)
    )  # type: int
    created = attrib(
        validator=instanceOf(DateTime)
    )  # type: DateTime
    summary = attrib(
        validator=optional(instanceOf(str))
    )  # type: Optional[str]
    reportEntries = attrib(
        validator=instanceOf(Iterable), convert=sortedTuple
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
