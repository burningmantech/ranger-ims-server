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
Tests for :mod:`ranger-ims-server.model._incident`
"""

from .datetimes import dt1, dt2
from .events import eventA
from .locations import theMan
from .rangers import rangerHubcap
from .._entry import ReportEntry
from .._incident import Incident, summaryFromReport
from .._priority import IncidentPriority
from .._state import IncidentState
from ...ext.trial import TestCase


__all__ = ()



entryA = ReportEntry(
    created=dt1,
    author=rangerHubcap.handle,
    automatic=True,
    text="State changed to: new",
)

entryB = ReportEntry(
    created=dt2,
    author=rangerHubcap.handle,
    automatic=False,
    text="A different thing happened",
)



class EventTests(TestCase):
    """
    Tests for :class:`Incident`
    """

    def test_str_summary(self) -> None:
        """
        :meth:`Incident.__str__` renders an incident with a summary as a
        string.
        """
        incident = Incident(
            event=eventA,
            number=123,
            created=dt1,
            state=IncidentState.new,
            priority=IncidentPriority.normal,
            summary="A thing happened",
            rangers=(),
            incidentTypes=(),
            location=theMan,
            reportEntries=(),
        )

        self.assertEqual(str(incident), "123: A thing happened")


    def test_str_report(self) -> None:
        """
        :meth:`Incident.__str__` renders an incident without a summary as a
        string.
        """
        incident = Incident(
            event=eventA,
            number=321,
            created=dt1,
            state=IncidentState.new,
            priority=IncidentPriority.normal,
            summary=None,
            rangers=(),
            incidentTypes=(),
            location=theMan,
            reportEntries=(entryB,),
        )

        self.assertEqual(str(incident), "321: A different thing happened")



class SummaryFromReportTests(TestCase):
    """
    Tests for :func:`summaryFromReport`
    """

    def test_summary(self) -> None:
        """
        :func:`summaryFromReport` uses the given non-empty summary.
        """
        result = summaryFromReport(
            summary="A thing happened",
            reportEntries=(),
        )

        self.assertEqual(result, "A thing happened")


    def test_entryAutomatic(self) -> None:
        """
        :func:`summaryFromReport` skips automatic entries.
        """
        result = summaryFromReport(
            summary="",
            reportEntries=(entryA, entryB),
        )

        self.assertEqual(result, entryB.text)


    def test_entryNotAutomatic(self) -> None:
        """
        :func:`summaryFromReport` uses first entry.
        """
        result = summaryFromReport(
            summary="",
            reportEntries=(entryB,),
        )

        self.assertEqual(result, entryB.text)


    def test_entryNone(self) -> None:
        """
        :func:`summaryFromReport` returns am empty string if given no report
        entries.
        """
        result = summaryFromReport(
            summary=None,
            reportEntries=(),
        )

        self.assertEqual(result, "")
