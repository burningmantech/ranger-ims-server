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

from ._address import RodGarettAddressJSONKey
from ._json import (
    jsonDeserialize, jsonSerialize, registerDeserializer, registerSerializer
)
from .._address import TextOnlyAddress, RodGarettAddress
from .._location import Location


__all__ = ()


# cattrs default serialization works.
# We need custom deserialization because Address is an ABC and we need to
# figure out which subclass to deserialize into.



def deserializeLocation(
    cl: Type, obj: Dict[str, Any]
) -> Location:
    assert cl is Location, (cl, obj)

    jsonAddress = obj["address"]

    for key in RodGarettAddressJSONKey:
        if key.name == "description":
            continue
        if key.name in jsonAddress:
            addressClass = RodGarettAddress
            break
    else:
        addressClass = TextOnlyAddress

    return Location(
        name=obj["name"],
        address=jsonDeserialize(obj["address"], addressClass),
    )


registerDeserializer(Location, deserializeLocation)
