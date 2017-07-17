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

from datetime import datetime as DateTime
from typing import Any, Iterable

from attr import asdict

from hypothesis import given
from hypothesis.strategies import lists, sampled_from, text

from ims.ext.trial import TestCase

from .._entry import ReportEntry
from .._event import Event
from .._incident import Incident, summaryFromReport
from .._location import Location
from .._priority import IncidentPriority
from .._state import IncidentState
from ..strategies import (
    dateTimes, events, incidentNumbers, incidentPriorities, incidentStates,
    incidentSummaries, incidentTypes, incidents, locations, rangerHandles,
    reportEntries,
)

__all__ = ()



class IncidentTests(TestCase):
    """
    Tests for :class:`Incident`
    """

    @given(incidents(), text(min_size=1))
    def test_str_summary(self, incident: Incident, summary: str) -> None:
        """
        :meth:`Incident.__str__` renders an incident with a non-empty summary
        as a string consisting of the incident number and summary.
        """
        incident = incident.replace(summary=summary)

        self.assertEqual(
            str(incident), "{}: {}".format(incident.number, summary)
        )


    @given(incidents(), sampled_from((None, "")))
    def test_str_noSummary(self, incident: Incident, summary) -> None:
        """
        :meth:`Incident.__str__` renders an incident without a summary as a
        string.
        """
        incident = incident.replace(summary=summary)

        self.assertEqual(
            str(incident),
            "{}: {}".format(
                incident.number,
                summaryFromReport(None, incident.reportEntries),
            )
        )


    def _test_replace(self, incident: Incident, name: str, value: Any) -> None:
        mod = {name: value}
        new = incident.replace(**mod)

        expected = asdict(incident, recurse=False)
        expected.update(mod)

        self.assertEqual(asdict(new, recurse=False), expected)


    @given(incidents(), events())
    def test_replace_event(self, incident: Incident, event: Event) -> None:
        """
        :meth:`Incident.replace` with an event argument replaces the event.
        """
        self._test_replace(incident, "event", event)


    @given(incidents(), incidentNumbers())
    def test_replace_number(self, incident: Incident, number: int) -> None:
        """
        :meth:`Incident.replace` with a number argument replaces the
        incident number.
        """
        self._test_replace(incident, "number", number)


    @given(incidents(), dateTimes())
    def test_replace_created(
        self, incident: Incident, created: DateTime
    ) -> None:
        """
        :meth:`Incident.replace` with a created argument replaces the created
        time.
        """
        self._test_replace(incident, "created", created)


    @given(incidents(), incidentStates())
    def test_replace_state(
        self, incident: Incident, state: IncidentState
    ) -> None:
        """
        :meth:`Incident.replace` with a state argument replaces the incident
        state.
        """
        self._test_replace(incident, "state", state)


    @given(incidents(), incidentPriorities())
    def test_replace_priority(
        self, incident: Incident, priority: IncidentPriority
    ) -> None:
        """
        :meth:`Incident.replace` with a priority argument replaces the incident
        priority.
        """
        self._test_replace(incident, "priority", priority)


    @given(incidents(), incidentSummaries())
    def test_replace_summary(self, incident: Incident, summary: str) -> None:
        """
        :meth:`Incident.replace` with a summary argument replaces the incident
        summary.
        """
        self._test_replace(incident, "summary", summary)


    @given(incidents(), locations())
    def test_replace_location(
        self, incident: Incident, location: Location
    ) -> None:
        """
        :meth:`Incident.replace` with a location argument replaces the
        location.
        """
        self._test_replace(incident, "location", location)


    @given(incidents(), lists(rangerHandles()))
    def test_replace_rangerHandles(
        self, incident: Incident, rangerHandles: Iterable[str]
    ) -> None:
        """
        :meth:`Incident.replace` with a rangerHandles argument replaces the
        Ranger handles.
        """
        self._test_replace(incident, "rangerHandles", frozenset(rangerHandles))


    @given(incidents(), lists(incidentTypes()))
    def test_replace_incidentTypes(
        self, incident: Incident, incidentTypes: Iterable[str]
    ) -> None:
        """
        :meth:`Incident.replace` with a incidentTypes argument replaces the
        incident types.
        """
        self._test_replace(incident, "incidentTypes", frozenset(incidentTypes))


    @given(incidents(), lists(reportEntries()))
    def test_replace_reportEntries(
        self, incident: Incident, reportEntries: Iterable[ReportEntry]
    ) -> None:
        """
        :meth:`Incident.replace` with a reportEntries argument replaces the
        report entries.
        """
        self._test_replace(
            incident, "reportEntries", tuple(sorted(reportEntries))
        )



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



    @given(lists(reportEntries()))
    def test_entryAutomatic(
        self, reportEntries: Iterable[ReportEntry]
    ) -> None:
        """
        :func:`summaryFromReport` skips automatic entries.
        """
        self.assertEqual(
            summaryFromReport(summary="", reportEntries=reportEntries),
            summaryFromReport(
                summary="",
                reportEntries=(r for r in reportEntries if not r.automatic),
            )
        )


    @given(lists(reportEntries(), min_size=1))
    def test_entryNotAutomatic(
        self, reportEntries: Iterable[ReportEntry]
    ) -> None:
        """
        :func:`summaryFromReport` uses the first line of text from the first
        non-automatic entry.
        """
        for entry in reportEntries:
            if not entry.automatic:
                expectedSummary = entry.text.split("\n")[0]
                break
        else:
            expectedSummary = ""

        self.assertEqual(
            summaryFromReport(summary="", reportEntries=reportEntries),
            expectedSummary,
        )


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
