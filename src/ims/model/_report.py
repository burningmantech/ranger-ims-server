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

from collections.abc import Iterable
from datetime import datetime as DateTime
from typing import Optional, Sequence

from attr import attrib, attrs
from attr.validators import instance_of, optional

from ims.ext.attr import sorted_tuple

from ._incident import summaryFromReport
from ._replace import ReplaceMixIn

Optional, Sequence  # Silence linter


__all__ = ()



@attrs(frozen=True)
class IncidentReport(ReplaceMixIn):
    """
    Incident
    """

    # FIXME: better validator for reportEntries

    number: int = attrib(
        validator=instance_of(int)
    )
    created: DateTime = attrib(
        validator=instance_of(DateTime)
    )
    summary: Optional[str] = attrib(
        validator=optional(instance_of(str))
    )
    reportEntries: Sequence = attrib(
        validator=instance_of(Iterable), convert=sorted_tuple
    )


    def __str__(self) -> str:
        return f"{self.number}: {self.summaryFromReport()}"


    def summaryFromReport(self) -> str:
        """
        Generate a summary by either using ``self.summary`` if it is not
        :obj:`None` or empty, or the first line of the first report entry.
        """
        return summaryFromReport(self.summary, self.reportEntries)
