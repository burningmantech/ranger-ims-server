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
from typing import Any, Dict, Type

from ._json import jsonDeserialize, registerDeserializer
from .._address import RodGarettAddress, TextOnlyAddress
from .._location import Location


__all__ = ()


@unique
class LocationJSONKey(Enum):
    """
    Location JSON keys
    """

    name                 = "name"
    address              = "address"
    addressType          = "type"
    addressTypeText      = "text"
    addressTypeRodGarett = "garett"


# cattrs default serialization works.
# We need custom deserialization because Address is an ABC and we need to
# figure out which subclass to deserialize into.



def deserializeLocation(obj: Dict[str, Any], cl: Type) -> Location:
    assert cl is Location, (cl, obj)

    jsonAddress = obj[LocationJSONKey.address.value]
    addressType = jsonAddress[LocationJSONKey.addressType.value]

    addressClass: Type
    if addressType == LocationJSONKey.addressTypeRodGarett.value:
        addressClass = RodGarettAddress
    elif addressType == LocationJSONKey.addressTypeText.value:
        addressClass = TextOnlyAddress
    else:
        raise ValueError("Unknown address type: {}".format(addressType))

    return Location(
        name=obj[LocationJSONKey.name.value],
        address=jsonDeserialize(
            obj[LocationJSONKey.address.value], addressClass
        ),
    )


registerDeserializer(Location, deserializeLocation)
