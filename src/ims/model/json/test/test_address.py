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
Tests for :mod:`ranger-ims-server.model.json._address`
"""

from typing import Any, Callable, Dict, Tuple

from hypothesis import given
from hypothesis.strategies import composite, integers, text

from .._json import jsonDeserialize, jsonSerialize
from ..._address import RodGarettAddress, TextOnlyAddress
from ....ext.trial import TestCase


__all__ = ()


TextOnlyAddressAndJSON  = Tuple[TextOnlyAddress, Dict[str, Any]]
RodGarettAddressAndJSON = Tuple[RodGarettAddress, Dict[str, Any]]


@composite
def textOnlyAddressesAndJSON(draw: Callable) -> TextOnlyAddressAndJSON:
    description = draw(text())

    address = TextOnlyAddress(description=description)

    json = dict(description=jsonSerialize(description))

    return (address, json)


@composite
def rodGarettAddressesAndJSON(draw: Callable) -> RodGarettAddressAndJSON:
    concentric   = draw(integers(min_value=0, max_value=12))
    radialHour   = draw(integers(min_value=1, max_value=12))
    radialMinute = draw(integers(min_value=0, max_value=59))
    description  = draw(text())

    address = RodGarettAddress(
        concentric=concentric,
        radialHour=radialHour,
        radialMinute=radialMinute,
        description=description,
    )

    json = dict(
        concentric=jsonSerialize(concentric),
        radial_hour=jsonSerialize(radialHour),
        radial_minute=jsonSerialize(radialMinute),
        description=jsonSerialize(description),
    )

    return (address, json)



class TextOnlyAddressSerializationTests(TestCase):
    """
    Tests for serialization of :class:`TextOnlyAddress`
    """

    @given(textOnlyAddressesAndJSON())
    def test_serialize(
        self, textOnlyAddressAndJSON: TextOnlyAddressAndJSON
    ) -> None:
        """
        :func:`jsonSerialize` serializes the given address.
        """
        address, json = textOnlyAddressAndJSON

        self.assertEqual(jsonSerialize(address), json)



class RodGarettAddressSerializationTests(TestCase):
    """
    Tests for serialization of :class:`RodGarettAddress`
    """

    @given(rodGarettAddressesAndJSON())
    def test_serialize(
        self, rodGarettAddressAndJSON: RodGarettAddressAndJSON
    ) -> None:
        """
        :func:`jsonSerialize` serializes the given address.
        """
        address, json = rodGarettAddressAndJSON

        self.assertEqual(jsonSerialize(address), json)



class TextOnlyAddressDeserializationTests(TestCase):
    """
    Tests for deserialization of :class:`TextOnlyAddress`
    """

    @given(textOnlyAddressesAndJSON())
    def test_deserialize(
        self, textOnlyAddressAndJSON: TextOnlyAddressAndJSON
    ) -> None:
        """
        :func:`jsonDeserialize` returns a address with the correct data.
        """
        address, json = textOnlyAddressAndJSON

        self.assertEqual(jsonDeserialize(json, TextOnlyAddress), address)



class RodGarettAddressDeserializationTests(TestCase):
    """
    Tests for deserialization of :class:`RodGarettAddress`
    """

    @given(rodGarettAddressesAndJSON())
    def test_deserialize(
        self, rodGarettAddressAndJSON: RodGarettAddressAndJSON
    ) -> None:
        """
        :func:`jsonDeserialize` returns a address with the correct data.
        """
        address, json = rodGarettAddressAndJSON

        self.assertEqual(jsonDeserialize(json, RodGarettAddress), address)
