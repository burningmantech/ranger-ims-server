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
Tests for :mod:`ranger-ims-server.model.json._location`
"""

from typing import Any, Callable, Dict, Tuple

from hypothesis import given
from hypothesis.strategies import choices, composite, integers, text


from .._json import jsonDeserialize, jsonSerialize
from ..._address import Address, RodGarettAddress, TextOnlyAddress
from ..._location import Location
from ....ext.trial import TestCase


__all__ = ()


LocationAndJSON = Tuple[Location, Dict[str, Any]]


@composite
def textOnlyAddresses(draw: Callable) -> TextOnlyAddress:
    description = draw(text())

    return TextOnlyAddress(description=description)


@composite
def rodGarettAddresses(draw: Callable) -> RodGarettAddress:
    concentric   = draw(integers(min_value=0, max_value=12))
    radialHour   = draw(integers(min_value=1, max_value=12))
    radialMinute = draw(integers(min_value=0, max_value=59))
    description  = draw(text())

    return RodGarettAddress(
        concentric=concentric,
        radialHour=radialHour,
        radialMinute=radialMinute,
        description=description,
    )


@composite
def addresses(draw: Callable) -> Address:
    choice = draw(choices())
    addresses = choice((textOnlyAddresses, rodGarettAddresses))
    return draw(addresses())


@composite
def locationsAndJSON(draw: Callable) -> LocationAndJSON:
    name    = draw(text())
    address = draw(addresses())

    location = Location(name=name, address=address)

    json = dict(name=jsonSerialize(name), address=jsonSerialize(address))

    return (location, json)



class LocationSerializationTests(TestCase):
    """
    Tests for serialization of :class:`Location`
    """

    @given(locationsAndJSON())
    def test_serialize(self, locationAndJSON: LocationAndJSON) -> None:
        """
        :func:`jsonSerialize` serializes the given location.
        """
        location, json = locationAndJSON

        self.assertEqual(jsonSerialize(location), json)



class LocationDeserializationTests(TestCase):
    """
    Tests for deserialization of :class:`Location`
    """

    @given(locationsAndJSON())
    def test_deserialize(self, locationAndJSON: LocationAndJSON) -> None:
        """
        :func:`jsonDeserialize` returns a location with the correct data.
        """
        location, json = locationAndJSON

        self.assertEqual(jsonDeserialize(json, Location), location)
