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

from hypothesis import given

from .json import jsonFromRodGarettAddress, jsonFromTextOnlyAddress
from .strategies import rodGarettAddresses, textOnlyAddresses
from .._json import jsonDeserialize, jsonSerialize
from ..._address import RodGarettAddress, TextOnlyAddress
from ....ext.trial import TestCase


__all__ = ()



class TextOnlyAddressSerializationTests(TestCase):
    """
    Tests for serialization of :class:`TextOnlyAddress`
    """

    @given(textOnlyAddresses())
    def test_serialize(self, address: TextOnlyAddress) -> None:
        """
        :func:`jsonSerialize` serializes the given address.
        """
        self.assertEqual(
            jsonSerialize(address), jsonFromTextOnlyAddress(address)
        )



class RodGarettAddressSerializationTests(TestCase):
    """
    Tests for serialization of :class:`RodGarettAddress`
    """

    @given(rodGarettAddresses())
    def test_serialize(
        self, address: RodGarettAddress
    ) -> None:
        """
        :func:`jsonSerialize` serializes the given address.
        """
        self.assertEqual(
            jsonSerialize(address), jsonFromRodGarettAddress(address)
        )



class TextOnlyAddressDeserializationTests(TestCase):
    """
    Tests for deserialization of :class:`TextOnlyAddress`
    """

    @given(textOnlyAddresses())
    def test_deserialize(self, address: TextOnlyAddress) -> None:
        """
        :func:`jsonDeserialize` returns a address with the correct data.
        """
        self.assertEqual(
            jsonDeserialize(jsonFromTextOnlyAddress(address), TextOnlyAddress),
            address
        )



class RodGarettAddressDeserializationTests(TestCase):
    """
    Tests for deserialization of :class:`RodGarettAddress`
    """

    @given(rodGarettAddresses())
    def test_deserialize(self, address: RodGarettAddress) -> None:
        """
        :func:`jsonDeserialize` returns a address with the correct data.
        """
        self.assertEqual(
            jsonDeserialize(
                jsonFromRodGarettAddress(address), RodGarettAddress
            ),
            address
        )
