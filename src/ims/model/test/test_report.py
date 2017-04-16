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
from .events import eventA
from .locations import theMan
from .rangers import rangerHubcap
from .._entry import ReportEntry
from .._incident import Incident
from .._priority import IncidentPriority
from .._state import IncidentState
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
            reportEntries=(entry,),
        )

        self.assertEqual(str(incident), "321: A different thing happened")
