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
from typing import Any, Dict, Optional, Type, cast

from ._json import (
    deserialize,
    jsonSerialize,
    registerDeserializer,
    registerSerializer,
)
from .._address import Address, RodGarettAddress, TextOnlyAddress


__all__ = ()


# cattrs defaults for TextOnlyAddress work, but RodGarettAddress requires key
# remapping.


@unique
class AddressTypeJSONValue(Enum):
    """
    Address type JSON values
    """

    text = "text"
    rodGarett = "garett"


@unique
class AddressJSONKey(Enum):
    """
    Generic address JSON keys
    """

    addressType = "type"
    description = "description"


class AddressJSONType(Enum):
    """
    Text-only address attribute types
    """

    addressType = str
    description = cast(Type[Any], Optional[str])


@unique
class TextOnlyAddressJSONKey(Enum):
    """
    Text-only address JSON keys
    """

    description = AddressJSONKey.description.value


class TextOnlyAddressJSONType(Enum):
    """
    Text-only address attribute types
    """

    description = AddressJSONType.description.value


@unique
class RodGarettAddressJSONKey(Enum):
    """
    Rod Garett address JSON keys
    """

    concentric = "concentric"
    radialHour = "radial_hour"
    radialMinute = "radial_minute"
    description = AddressJSONKey.description.value


class RodGarettAddressJSONType(Enum):
    """
    Rod Garett address JSON keys
    """

    concentric = Optional[str]
    radialHour = Optional[int]
    radialMinute = Optional[int]
    description = AddressJSONType.description.value


def serializeAddress(address: Address) -> Dict[str, Any]:
    if isinstance(address, TextOnlyAddress):
        return serializeTextOnlyAddress(address)
    elif isinstance(address, RodGarettAddress):
        return serializeRodGarettAddress(address)
    else:
        raise TypeError(f"Unknown address type: {address!r}")


registerSerializer(Address, serializeAddress)


def serializeTextOnlyAddress(address: TextOnlyAddress) -> Dict[str, Any]:
    # Map TextOnlyAddress attribute names to JSON dict key names
    json = dict(
        (key.value, jsonSerialize(getattr(address, key.name)))
        for key in TextOnlyAddressJSONKey
    )
    json["type"] = "text"
    return json


registerSerializer(TextOnlyAddress, serializeTextOnlyAddress)


def serializeRodGarettAddress(address: RodGarettAddress) -> Dict[str, Any]:
    # Map RodGarettAddress attribute names to JSON dict key names
    json = dict(
        (key.value, jsonSerialize(getattr(address, key.name)))
        for key in RodGarettAddressJSONKey
    )
    json["type"] = "garett"
    return json


registerSerializer(RodGarettAddress, serializeRodGarettAddress)


def deserializeTextOnlyAddress(
    obj: Dict[str, Any], cl: Type
) -> TextOnlyAddress:
    assert cl is TextOnlyAddress, (cl, obj)

    return cast(
        TextOnlyAddress,
        deserialize(
            obj,
            TextOnlyAddress,
            TextOnlyAddressJSONType,
            TextOnlyAddressJSONKey,
        ),
    )


registerDeserializer(TextOnlyAddress, deserializeTextOnlyAddress)


def deserializeRodGarettAddress(
    obj: Dict[str, Any], cl: Type
) -> RodGarettAddress:
    assert cl is RodGarettAddress, (cl, obj)

    return cast(
        RodGarettAddress,
        deserialize(
            obj,
            RodGarettAddress,
            RodGarettAddressJSONType,
            RodGarettAddressJSONKey,
        ),
    )


registerDeserializer(RodGarettAddress, deserializeRodGarettAddress)
