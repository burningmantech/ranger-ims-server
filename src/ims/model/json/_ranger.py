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
from typing import Any, Optional, cast

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
    name = "name"
    status = "status"
    email = "email"
    enabled = "enabled"
    directoryID = "directory_id"


class RangerJSONType(Enum):
    """
    Ranger attribute types
    """

    handle = str
    name = str  # type: ignore[assignment]
    status = RangerStatus
    email = set[str]
    enabled = bool
    directoryID = Optional[str]


def serializeRanger(ranger: Ranger) -> dict[str, Any]:
    # Map Ranger attribute names to JSON dict key names
    return {
        key.value: jsonSerialize(getattr(ranger, key.name))
        for key in RangerJSONKey
    }


registerSerializer(Ranger, serializeRanger)


def deserializeRanger(obj: dict[str, Any], cl: type[Ranger]) -> Ranger:
    assert cl is Ranger, (cl, obj)

    return cast(Ranger, deserialize(obj, Ranger, RangerJSONType, RangerJSONKey))


registerDeserializer(Ranger, deserializeRanger)


class RangerStatusJSONValue(Enum):
    """
    Ranger status JSON values
    """

    active = "active"
    inactive = "inactive"
    vintage = "vintage"
    other = "(unknown)"


def serializeRangerStatus(rangerStatus: RangerStatus) -> str:
    return cast(str, getattr(RangerStatusJSONValue, rangerStatus.name).value)


registerSerializer(RangerStatus, serializeRangerStatus)


def deserializeRangerStatus(obj: int, cl: type[RangerStatus]) -> RangerStatus:
    assert cl is RangerStatus, (cl, obj)

    return cast(
        RangerStatus, getattr(RangerStatus, RangerStatusJSONValue(obj).name)
    )


registerDeserializer(RangerStatus, deserializeRangerStatus)
