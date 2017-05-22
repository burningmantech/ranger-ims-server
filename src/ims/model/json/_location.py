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

from typing import Any, Dict, Type

from ._json import jsonDeserialize, registerDeserializer
from .._address import RodGarettAddress, TextOnlyAddress
from .._location import Location


__all__ = ()


# cattrs default serialization works.
# We need custom deserialization because Address is an ABC and we need to
# figure out which subclass to deserialize into.



def deserializeLocation(obj: Dict[str, Any], cl: Type) -> Location:
    assert cl is Location, (cl, obj)

    jsonAddress = obj["address"]
    addressType = jsonAddress["type"]

    if addressType == "garett":
        addressClass = RodGarettAddress  # type: Type
    elif addressType == "text":
        addressClass = TextOnlyAddress
    else:
        raise ValueError("unknown address type: {}".format(addressType))

    return Location(
        name=obj["name"],
        address=jsonDeserialize(obj["address"], addressClass),
    )


registerDeserializer(Location, deserializeLocation)
