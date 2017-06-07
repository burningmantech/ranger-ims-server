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

from ims.ext.trial import TestCase

from .datetimes import dt1, dt2
from .rangers import rangerBucket, rangerHubcap
from .._entry import ReportEntry


__all__ = ()



class ReportEntryTests(TestCase):
    """
    Tests for :class:`ReportEntry`
    """

    text = "Hello"


    def test_ordering_created(self) -> None:
        """
        Report entry ordering sorts by created.
        """
        b = ReportEntry(
            created=dt2,
            author=rangerHubcap.handle,
            automatic=False,
            text=self.text,
        )

        a = ReportEntry(
            created=dt1,
            author=rangerHubcap.handle,
            automatic=False,
            text=self.text,
        )

        self.assertLess(a, b)
        self.assertLessEqual(a, b)
        self.assertNotEqual(a, b)
        self.assertGreater(b, a)
        self.assertGreaterEqual(b, a)


    def test_ordering_author(self) -> None:
        """
        Report entry ordering with same created sorts by author.
        """
        b = ReportEntry(
            created=dt1,
            author=rangerHubcap.handle,
            automatic=False,
            text=self.text,
        )

        a = ReportEntry(
            created=dt1,
            author=rangerBucket.handle,
            automatic=False,
            text=self.text,
        )

        self.assertLess(a, b)
        self.assertLessEqual(a, b)
        self.assertNotEqual(a, b)
        self.assertGreater(b, a)
        self.assertGreaterEqual(b, a)


    def test_ordering_automatic(self) -> None:
        """
        Report entry ordering with same created and author sorts by automatic,
        where :obj:`True` comes before :obj:`False`.
        """
        b = ReportEntry(
            created=dt1,
            author=rangerHubcap.handle,
            automatic=False,
            text=self.text,
        )

        a = ReportEntry(
            created=dt1,
            author=rangerHubcap.handle,
            automatic=True,
            text=self.text,
        )

        self.assertLess(a, b)
        self.assertLessEqual(a, b)
        self.assertNotEqual(a, b)
        self.assertGreater(b, a)
        self.assertGreaterEqual(b, a)


    def test_eq(self) -> None:
        """
        Test equality.
        """
        a = ReportEntry(
            created=dt1,
            author=rangerHubcap.handle,
            automatic=True,
            text=self.text,
        )

        b = ReportEntry(
            created=dt1,
            author=rangerHubcap.handle,
            automatic=True,
            text=self.text,
        )

        self.assertEqual(a, b)


    def test_eq_otherType(self) -> None:
        """
        Test equality with another type.
        """
        a = ReportEntry(
            created=dt1,
            author=rangerHubcap.handle,
            automatic=True,
            text=self.text,
        )

        self.assertNotEqual(a, object())
