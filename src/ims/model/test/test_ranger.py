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

from hypothesis import given

from ims.ext.trial import TestCase

from .._ranger import Ranger, RangerStatus, statusDescriptions
from ..strategies import rangers


__all__ = ()


class RangerStatusTests(TestCase):
    """
    Tests for :class:`RangerStatus`
    """

    def test_repr(self) -> None:
        """
        Ranger status renders as a string.
        """
        for status in RangerStatus:
            self.assertEqual(
                repr(status), f"{RangerStatus.__name__}[{status.name!r}]"
            )

    def test_str(self) -> None:
        """
        Ranger status renders as a string.
        """
        for status in RangerStatus:
            self.assertEqual(str(status), statusDescriptions[status.name])


class RangerTests(TestCase):
    """
    Tests for :class:`Ranger`
    """

    @given(rangers())
    def test_str(self, ranger: Ranger) -> None:
        """
        Ranger status renders as a string.
        """
        self.assertEqual(
            str(ranger), f"{ranger.status} {ranger.handle} ({ranger.name})"
        )
