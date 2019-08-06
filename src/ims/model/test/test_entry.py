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
Tests for :mod:`ranger-ims-server.model._entry`
"""

from datetime import datetime as DateTime

from hypothesis import given
from hypothesis.strategies import booleans

from ims.ext.trial import TestCase

from .._convert import normalizeDateTime
from .._entry import ReportEntry
from ..strategies import dateTimes, rangerHandles, reportEntries


__all__ = ()



class ReportEntryTests(TestCase):
    """
    Tests for :class:`ReportEntry`
    """

    text = "Hello"


    @given(reportEntries())
    def test_str(self, reportEntry: ReportEntry) -> None:
        """
        Report entry renders as a string.
        """
        star = "*" if reportEntry.automatic else ""
        self.assertEqual(
            str(reportEntry),
            f"{reportEntry.created} {reportEntry.author}"
            f"{star}: {reportEntry.text}"
        )


    @given(reportEntries(), dateTimes(), dateTimes())
    def test_ordering_created(
        self, reportEntry: ReportEntry, createdA: DateTime, createdB: DateTime
    ) -> None:
        """
        Report entry ordering sorts by created.
        """
        createdA = normalizeDateTime(createdA)
        createdB = normalizeDateTime(createdB)

        a = reportEntry.replace(created=createdA)
        b = reportEntry.replace(created=createdB)

        self.assertEqual(
            [r.created for r in sorted((a, b))],
            sorted((createdA, createdB))
        )


    @given(reportEntries(), rangerHandles(), rangerHandles())
    def test_ordering_author(
        self, reportEntry: ReportEntry, authorA: str, authorB: str
    ) -> None:
        """
        Report entry ordering with same created sorts by author.
        """
        a = reportEntry.replace(author=authorA)
        b = reportEntry.replace(author=authorB)

        self.assertEqual(
            [r.author for r in sorted((a, b))],
            sorted((authorA, authorB))
        )


    @given(reportEntries(), booleans(), booleans())
    def test_ordering_automatic(
        self, reportEntry: ReportEntry, autoA: bool, autoB: bool
    ) -> None:
        """
        Report entry ordering with same created and author sorts by automatic,
        where :obj:`True` comes before :obj:`False`.
        """
        a = reportEntry.replace(automatic=autoA)
        b = reportEntry.replace(automatic=autoB)

        self.assertEqual(
            [r.automatic for r in sorted((a, b))],
            list(reversed(sorted((autoA, autoB)))),
            (a, b)
        )


    @given(reportEntries())
    def test_eq(self, reportEntry: ReportEntry) -> None:
        """
        Test equality.
        """
        self.assertEqual(reportEntry, reportEntry.replace())


    @given(reportEntries())
    def test_neq(self, reportEntry: ReportEntry) -> None:
        """
        Test equality with another type.
        """
        self.assertNotEqual(reportEntry, object())
