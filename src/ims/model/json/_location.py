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
JSON serialization/deserialization for addresses
"""

from enum import Enum, unique
from typing import Any, Dict, Optional, Type

from ._address import AddressJSONKey, AddressTypeJSONValue, serializeAddress
from ._json import (
    jsonDeserialize,
    jsonSerialize,
    registerDeserializer,
    registerSerializer,
)
from .._address import Address, RodGarettAddress, TextOnlyAddress
from .._location import Location


__all__ = ()


@unique
class LocationJSONKey(Enum):
    """
    Location JSON keys
    """

    name = "name"


def serializeLocation(location: Location) -> Dict[str, Any]:
    # Map Location attribute names to JSON dict key names
    locationJSON = {
        key.value: jsonSerialize(getattr(location, key.name))
        for key in LocationJSONKey
    }

    addressJSON = serializeAddress(location.address)
    locationJSON.update(addressJSON)

    return locationJSON


registerSerializer(Location, serializeLocation)


def deserializeLocation(
    obj: Optional[Dict[str, Any]], cl: Type[Location]
) -> Location:
    assert cl is Location, (cl, obj)

    if obj is None:
        return Location(
            name=None,
            address=TextOnlyAddress(),
        )

    # If address were a nested dict, we'd do this:
    # jsonAddress = obj[LocationJSONKey.address.value]
    # But we flatten the JSON schema, so:
    jsonAddress = obj
    addressType = jsonAddress[AddressJSONKey.addressType.value]

    addressClass: Type[Address]
    if addressType == AddressTypeJSONValue.rodGarett.value:
        addressClass = RodGarettAddress
    elif addressType == AddressTypeJSONValue.text.value:
        addressClass = TextOnlyAddress
    else:
        raise ValueError(f"Unknown address type: {addressType}")

    return Location(
        name=obj.get(LocationJSONKey.name.value, None),
        address=jsonDeserialize(jsonAddress, addressClass),
    )


registerDeserializer(Location, deserializeLocation)
