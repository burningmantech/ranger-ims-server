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
Tests for :mod:`ranger-ims-server.model.jsons._report`
"""

from hypothesis import given

from ims.ext.trial import TestCase

from ..._report import FieldReport
from ...strategies import fieldReports
from .._json import jsonDeserialize, jsonSerialize
from .json_helpers import jsonFromFieldReport


__all__ = ()


class FieldReportSerializationTests(TestCase):
    """
    Tests for serialization of :class:`FieldReport`
    """

    @given(fieldReports())
    def test_serialize(self, report: FieldReport) -> None:
        """
        :func:`jsonSerialize` serializes the given report.
        """
        self.assertEqual(jsonSerialize(report), jsonFromFieldReport(report))


class FieldReportDeserializationTests(TestCase):
    """
    Tests for deserialization of :class:`FieldReport`
    """

    @given(fieldReports())
    def test_deserialize(self, report: FieldReport) -> None:
        """
        :func:`jsonDeserialize` returns a report with the correct data.
        """
        self.assertEqual(
            jsonDeserialize(jsonFromFieldReport(report), FieldReport),
            report,
        )
