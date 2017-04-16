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

from .datetimes import dt1
from .rangers import rangerHubcap
from .._entry import ReportEntry
from .._report import IncidentReport
from ...ext.trial import TestCase


__all__ = ()



entry = ReportEntry(
    created=dt1,
    author=rangerHubcap,
    automatic=False,
    text="A different thing happened",
)



class IncidentReportTests(TestCase):
    """
    Tests for :class:`IncidentReport`
    """

    def test_str_summary(self) -> None:
        """
        :meth:`IncidentReport.__str__` renders an report with a summary as a
        string.
        """
        report = IncidentReport(
            number=123,
            created=dt1,
            summary="A thing happened",
            reportEntries=(),
        )

        self.assertEqual(str(report), "123: A thing happened")


    def test_str_report(self) -> None:
        """
        :meth:`IncidentReport.__str__` renders an report without a summary as a
        string.
        """
        report = IncidentReport(
            number=321,
            created=dt1,
            summary=None,
            reportEntries=(entry,),
        )

        self.assertEqual(str(report), "321: A different thing happened")
