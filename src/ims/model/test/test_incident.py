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
from hypothesis.strategies import iterables

from ims.ext.trial import TestCase

from .datetimes import dt1, dt2
from .events import eventA
from .locations import theMan
from .rangers import rangerHubcap
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



class IncidentTests(TestCase):
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
            rangerHandles=(),
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
            rangerHandles=(),
            incidentTypes=(),
            location=theMan,
            reportEntries=(entryB,),
        )

        self.assertEqual(str(incident), "321: A different thing happened")


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


    @given(incidents(), iterables(rangerHandles()))
    def test_replace_rangerHandles(
        self, incident: Incident, rangerHandles: Iterable[str]
    ) -> None:
        """
        :meth:`Incident.replace` with a rangerHandles argument replaces the
        Ranger handles.
        """
        self._test_replace(incident, "rangerHandles", frozenset(rangerHandles))


    @given(incidents(), iterables(incidentTypes()))
    def test_replace_incidentTypes(
        self, incident: Incident, incidentTypes: Iterable[str]
    ) -> None:
        """
        :meth:`Incident.replace` with a incidentTypes argument replaces the
        incident types.
        """
        self._test_replace(incident, "incidentTypes", frozenset(incidentTypes))


    @given(incidents(), iterables(reportEntries()))
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
