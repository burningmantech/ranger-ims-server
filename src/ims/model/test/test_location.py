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
Tests for :mod:`ranger-ims-server.model._location`
"""

from ims.ext.trial import TestCase

from .._address import TextOnlyAddress
from .._location import Location


__all__ = ()


class LocationTests(TestCase):
    """
    Tests for :class:`Location`
    """

    def test_addressNone(self) -> None:
        """
        :class:`Location` converts a :obj:`None` address to a
        :class:`TextOnlyAddress`.
        """
        location = Location(name="Foo", address=None)

        self.assertEqual(location.address, TextOnlyAddress(description=None))
