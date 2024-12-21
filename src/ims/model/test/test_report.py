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
Tests for :mod:`ranger-ims-server.model._report`
"""

from hypothesis import given
from hypothesis.strategies import sampled_from, text

from ims.ext.trial import TestCase

from .._incident import summaryFromReport
from .._report import FieldReport
from ..strategies import fieldReports


__all__ = ()


class FieldReportTests(TestCase):
    """
    Tests for :class:`FieldReport`
    """

    @given(fieldReports(), text(min_size=1))
    def test_str_summary(self, fieldReport: FieldReport, summary: str) -> None:
        """
        :meth:`FieldReport.__str__` renders a field report with a
        non-empty summary as a string consisting of the incident number and
        summary.
        """
        fieldReport = fieldReport.replace(summary=summary)

        self.assertEqual(
            str(fieldReport),
            f"{fieldReport.eventID}#{fieldReport.number}: {summary}",
        )

    @given(fieldReports(), sampled_from((None, "")))
    def test_str_noSummary(self, fieldReport: FieldReport, summary: str) -> None:
        """
        :meth:`FieldReport.__str__` renders a field report without a
        summary as a string.
        """
        fieldReport = fieldReport.replace(summary=summary)

        self.assertEqual(
            str(fieldReport),
            f"{fieldReport.eventID}#{fieldReport.number}: "
            f"{summaryFromReport(None, fieldReport.reportEntries)}",
        )
