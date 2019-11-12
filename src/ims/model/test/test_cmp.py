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
Tests for :mod:`ranger-ims-server.model._cmp`
"""

from typing import Any

from attr import attrs

from ims.ext.trial import TestCase

from .._cmp import ComparisonMixIn


__all__ = ()



@attrs(frozen=True, auto_attribs=True, kw_only=True, order=False)
class Comparable(ComparisonMixIn):
    value: Any


    def _cmpValue(self) -> Any:
        return self.value



class ComparisonMixInTests(TestCase):
    """
    Tests for :class:`ComparisonMixIn`
    """

    def test_hash(self) -> None:
        """
        Hash.
        """
        self.assertEqual(hash(Comparable(value=1)), hash(Comparable(value=1)))
        self.assertNotEqual(
            hash(Comparable(value=1)), hash(Comparable(value=2))
        )


    def test_eq(self) -> None:
        """
        Equality.
        """
        self.assertTrue(Comparable(value=1).__eq__(Comparable(value=1)))
        self.assertFalse(Comparable(value=1).__eq__(Comparable(value=2)))

        self.assertIdentical(
            Comparable(value=1).__eq__(object()), NotImplemented
        )


    def test_ne(self) -> None:
        """
        Inequality.
        """
        self.assertFalse(Comparable(value=1).__ne__(Comparable(value=1)))
        self.assertTrue(Comparable(value=1).__ne__(Comparable(value=2)))

        self.assertIdentical(
            Comparable(value=1).__ne__(object()), NotImplemented
        )


    def test_lt(self) -> None:
        """
        Less-than comparison.
        """
        self.assertFalse(Comparable(value=1).__lt__(Comparable(value=1)))
        self.assertTrue(Comparable(value=1).__lt__(Comparable(value=2)))
        self.assertFalse(Comparable(value=2).__lt__(Comparable(value=1)))

        self.assertIdentical(
            Comparable(value=1).__lt__(object()), NotImplemented
        )


    def test_le(self) -> None:
        """
        Less-than-or-equal-to comparison.
        """
        self.assertTrue(Comparable(value=1).__le__(Comparable(value=1)))
        self.assertTrue(Comparable(value=1).__le__(Comparable(value=2)))
        self.assertFalse(Comparable(value=2).__le__(Comparable(value=1)))

        self.assertIdentical(
            Comparable(value=1).__le__(object()), NotImplemented
        )


    def test_gt(self) -> None:
        """
        Less-than comparison.
        """
        self.assertFalse(Comparable(value=1).__gt__(Comparable(value=1)))
        self.assertFalse(Comparable(value=1).__gt__(Comparable(value=2)))
        self.assertTrue(Comparable(value=2).__gt__(Comparable(value=1)))

        self.assertIdentical(
            Comparable(value=1).__gt__(object()), NotImplemented
        )


    def test_ge(self) -> None:
        """
        Less-than-or-equal-to comparison.
        """
        self.assertTrue(Comparable(value=1).__ge__(Comparable(value=1)))
        self.assertFalse(Comparable(value=1).__ge__(Comparable(value=2)))
        self.assertTrue(Comparable(value=2).__ge__(Comparable(value=1)))

        self.assertIdentical(
            Comparable(value=1).__le__(object()), NotImplemented
        )
