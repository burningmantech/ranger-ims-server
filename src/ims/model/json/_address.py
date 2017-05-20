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

from ._json import (
    jsonDeserialize, jsonSerialize, registerDeserializer, registerSerializer
)
from .._address import RodGarettAddress


__all__ = ()



# cattrs defaults for TextOnlyAddress work, but RodGarettAddress requires key
# remapping.


@unique
class RodGarettAddressJSONKey(Enum):
    """
    Rod Garett address JSON keys
    """

    concentric   = "concentric"
    radialHour   = "radial_hour"
    radialMinute = "radial_minute"
    description  = "description"



class RodGarettAddressJSONType(Enum):
    """
    Rod Garett address JSON keys
    """

    concentric   = int
    radialHour   = int
    radialMinute = int
    description  = str



def serializeRodGarettAddress(address: RodGarettAddress) -> Dict[str, Any]:
    # Map RodGarettAddress attribute names to JSON dict key names
    return dict(
        (key.value, jsonSerialize(getattr(address, key.name)))
        for key in RodGarettAddressJSONKey
    )


registerSerializer(RodGarettAddress, serializeRodGarettAddress)


def deserializeRodGarettAddress(
    cl: Type, obj: Dict[str, Any]
) -> RodGarettAddress:
    assert cl is RodGarettAddress, (cl, obj)

    return RodGarettAddress(
        # Map JSON dict key names to RodGarettAddress attribute names
        **dict(
            (
                key.name,
                jsonDeserialize(
                    obj[key.value],
                    getattr(RodGarettAddressJSONType, key.name).value
                )
            )
            for key in RodGarettAddressJSONKey
        )
    )


registerDeserializer(RodGarettAddress, deserializeRodGarettAddress)
