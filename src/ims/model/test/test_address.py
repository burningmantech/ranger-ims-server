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
Tests for :mod:`ranger-ims-server.model._address`
"""

from hypothesis import given
from hypothesis.strategies import text

from ims.ext.trial import TestCase

from .._address import RodGarettAddress, TextOnlyAddress


__all__ = ()


class AddressTests(TestCase):
    """
    Tests for :class:`Address`
    """

    @given(text())
    def test_hash(self, description: str) -> None:
        """
        :meth:`RodGarettAddress.__hash__` and :meth:`TextOnlyAddress.__hash__`
        return the same value for equal addresses.
        """
        self.assertEqual(
            hash(TextOnlyAddress(description=description)),
            hash(RodGarettAddress(description=description)),
        )
        self.assertNotEqual(
            hash(TextOnlyAddress(description=description)),
            hash(RodGarettAddress(description=description, concentric="1")),
        )
        self.assertNotEqual(
            hash(TextOnlyAddress(description=description)),
            hash(RodGarettAddress(description=description, radialMinute=1)),
        )
        self.assertNotEqual(
            hash(TextOnlyAddress(description=description)),
            hash(RodGarettAddress(description=description, radialHour=1)),
        )

    @given(text())
    def test_eq_address(self, description: str) -> None:
        """
        :class:`RodGarettAddress` and :class:`TextOnlyAddress` can compare
        with each other.
        """
        self.assertEqual(
            TextOnlyAddress(description=description),
            RodGarettAddress(description=description),
        )
        self.assertEqual(
            TextOnlyAddress(description=description),
            TextOnlyAddress(description=description),
        )
        self.assertEqual(
            RodGarettAddress(description=description),
            RodGarettAddress(description=description),
        )
        self.assertNotEqual(
            TextOnlyAddress(description=description),
            RodGarettAddress(description=description, concentric="1"),
        )
        self.assertNotEqual(
            TextOnlyAddress(description=description),
            RodGarettAddress(description=description, radialMinute=1),
        )
        self.assertNotEqual(
            TextOnlyAddress(description=description),
            RodGarettAddress(description=description, radialHour=1),
        )

    def test_eq_none(self) -> None:
        """
        :class:`RodGarettAddress` and :class:`TextOnlyAddress` can compare
        with :obj:`None`.
        """
        self.assertEqual(TextOnlyAddress(description=None), None)
        self.assertEqual(
            RodGarettAddress(
                description=None,
                concentric=None,
                radialMinute=None,
                radialHour=None,
            ),
            None,
        )
