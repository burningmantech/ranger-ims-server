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

from typing import Any, Callable, Dict, Tuple

from hypothesis import given
from hypothesis.extra.datetime import datetimes
from hypothesis.strategies import booleans, composite, integers, text

from .._json import jsonDeserialize, jsonSerialize
from ..._entry import ReportEntry
from ..._report import IncidentReport
from ....ext.trial import TestCase


__all__ = ()


ReportAndJSON = Tuple[IncidentReport, Dict[str, Any]]


@composite
def entries(draw: Callable) -> ReportEntry:
    created   = draw(datetimes())
    author    = draw(text(min_size=1))
    automatic = draw(booleans())
    entryText = draw(text(min_size=1))

    return ReportEntry(
        created=created, author=author, automatic=automatic, text=entryText
    )


@composite
def reportsAndJSON(draw: Callable) -> ReportAndJSON:
    number  = draw(integers(min_value=1))
    created = draw(datetimes())
    summary = draw(text(min_size=1))

    reportEntries = tuple(sorted(
        draw(entries())
        for i in range(draw(integers(min_value=0, max_value=10)))
    ))

    report = IncidentReport(
        number=number,
        created=created,
        summary=summary,
        reportEntries=reportEntries,
    )

    json = dict(
        number=jsonSerialize(number),
        created=jsonSerialize(created),
        summary=jsonSerialize(summary),
        report_entries=tuple(jsonSerialize(e) for e in reportEntries),
    )

    return (report, json)



class IncidentReportSerializationTests(TestCase):
    """
    Tests for serialization of :class:`IncidentReport`
    """

    @given(reportsAndJSON())
    def test_serialize(self, reportAndJSON: ReportAndJSON) -> None:
        """
        :func:`jsonSerialize` serializes the given report entry.
        """
        report, json = reportAndJSON

        self.assertEqual(jsonSerialize(report), json)



class IncidentReportDeserializationTests(TestCase):
    """
    Tests for deserialization of :class:`IncidentReport`
    """

    @given(reportsAndJSON())
    def test_deserialize(self, reportAndJSON: ReportAndJSON) -> None:
        """
        :func:`jsonDeserialize` returns a report entry with the correct data.
        """
        report, json = reportAndJSON

        self.assertEqual(jsonDeserialize(json, IncidentReport), report)
