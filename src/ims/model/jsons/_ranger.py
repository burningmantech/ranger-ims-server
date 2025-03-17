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
JSON serialization/deserialization for Rangers
"""

from enum import Enum, unique
from typing import Any, cast

from .._ranger import Ranger, RangerStatus
from ._json import (
    deserialize,
    jsonSerialize,
    registerDeserializer,
    registerSerializer,
)


__all__ = ()


@unique
class RangerJSONKey(Enum):
    """
    Ranger JSON keys
    """

    handle = "handle"
    status = "status"
    # email is intentionally not serialized, since no web client needs it
    onsite = "onsite"
    directoryID = "directory_id"
    # password is intentionally not serialized, since no web client needs it


class RangerJSONType(Enum):
    """
    Ranger attribute types
    """

    handle = str
    status = RangerStatus
    # email is intentionally not serialized, since no web client needs it
    onsite = bool
    directoryID = str | None
    # password is intentionally not serialized, since no web client needs it


def serializeRanger(ranger: Ranger) -> dict[str, Any]:
    # Map Ranger attribute names to JSON dict key names
    return {
        key.value: jsonSerialize(getattr(ranger, key.name)) for key in RangerJSONKey
    }


registerSerializer(Ranger, serializeRanger)


def deserializeRanger(obj: dict[str, Any], cl: type[Ranger]) -> Ranger:
    assert cl is Ranger, (cl, obj)

    return cast("Ranger", deserialize(obj, Ranger, RangerJSONType, RangerJSONKey))


registerDeserializer(Ranger, deserializeRanger)


class RangerStatusJSONValue(Enum):
    """
    Ranger status JSON values
    """

    active = "active"
    inactive = "inactive"
    inactiveExtension = "inactiveExtension"
    other = "(unknown)"


def serializeRangerStatus(rangerStatus: RangerStatus) -> str:
    return cast("str", getattr(RangerStatusJSONValue, rangerStatus.name).value)


registerSerializer(RangerStatus, serializeRangerStatus)


def deserializeRangerStatus(obj: int, cl: type[RangerStatus]) -> RangerStatus:
    assert cl is RangerStatus, (cl, obj)

    return cast("RangerStatus", getattr(RangerStatus, RangerStatusJSONValue(obj).name))


registerDeserializer(RangerStatus, deserializeRangerStatus)
