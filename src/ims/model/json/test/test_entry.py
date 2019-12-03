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
Tests for :mod:`ranger-ims-server.model.json._entry`
"""

from hypothesis import given

from ims.ext.trial import TestCase

from .json import jsonFromReportEntry
from .._json import jsonDeserialize, jsonSerialize
from ..._entry import ReportEntry
from ...strategies import reportEntries


__all__ = ()


class ReportEntrySerializationTests(TestCase):
    """
    Tests for serialization of :class:`ReportEntry`
    """

    @given(reportEntries())
    def test_serialize(self, entry: ReportEntry) -> None:
        """
        :func:`jsonSerialize` serializes the given report entry.
        """
        self.assertEqual(jsonSerialize(entry), jsonFromReportEntry(entry))


class ReportEntryDeserializationTests(TestCase):
    """
    Tests for deserialization of :class:`ReportEntry`
    """

    @given(reportEntries())
    def test_deserialize(self, entry: ReportEntry) -> None:
        """
        :func:`jsonDeserialize` returns a report entry with the correct data.
        """
        self.assertEqual(
            jsonDeserialize(jsonFromReportEntry(entry), ReportEntry), entry
        )
