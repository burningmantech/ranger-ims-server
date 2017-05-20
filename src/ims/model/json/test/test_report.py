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
Tests for :mod:`ranger-ims-server.model.json._report`
"""

from hypothesis import given

from .json import jsonFromIncidentReport
from .strategies import incidentReports
from .._json import jsonDeserialize, jsonSerialize
from ..._report import IncidentReport
from ....ext.trial import TestCase


__all__ = ()



class IncidentReportSerializationTests(TestCase):
    """
    Tests for serialization of :class:`IncidentReport`
    """

    @given(incidentReports())
    def test_serialize(self, report: IncidentReport) -> None:
        """
        :func:`jsonSerialize` serializes the given report.
        """
        self.assertEqual(jsonSerialize(report), jsonFromIncidentReport(report))



class IncidentReportDeserializationTests(TestCase):
    """
    Tests for deserialization of :class:`IncidentReport`
    """

    @given(incidentReports())
    def test_deserialize(self, report: IncidentReport) -> None:
        """
        :func:`jsonDeserialize` returns a report with the correct data.
        """
        self.assertEqual(
            jsonDeserialize(jsonFromIncidentReport(report), IncidentReport),
            report
        )
