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
Tests for :mod:`ranger-ims-server.model.jsons._location`
"""

from hypothesis import given

from ims.ext.trial import TestCase

from ..._address import TextOnlyAddress
from ..._location import Location
from ...strategies import locations
from .._json import jsonDeserialize, jsonSerialize
from .json_helpers import jsonFromLocation


__all__ = ()


class LocationSerializationTests(TestCase):
    """
    Tests for serialization of :class:`Location`
    """

    @given(locations())
    def test_serialize(self, location: Location) -> None:
        """
        :func:`jsonSerialize` serializes the given location.
        """
        self.assertEqual(jsonSerialize(location), jsonFromLocation(location))


class LocationDeserializationTests(TestCase):
    """
    Tests for deserialization of :class:`Location`
    """

    @given(locations())
    def test_deserialize(self, location: Location) -> None:
        """
        :func:`jsonDeserialize` returns a location with the correct data.
        """
        self.assertEqual(
            jsonDeserialize(jsonFromLocation(location), Location), location
        )

    def test_deserialize_invalidType(self) -> None:
        """
        :func:`jsonDeserialize` returns a location with the correct data.
        """
        json = jsonFromLocation(
            Location(name="Foo", address=TextOnlyAddress(description="Over there"))
        )

        # jsonAddress = json["address"]
        jsonAddress = json

        jsonAddress["type"] = "* not a valid type *"

        self.assertRaises(ValueError, jsonDeserialize, json, Location)
