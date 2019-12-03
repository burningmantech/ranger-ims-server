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
JSON serialization/deserialization for event access
"""

from enum import Enum, unique
from typing import Any, Dict, FrozenSet, Type, cast

from ._json import (
    deserialize,
    jsonSerialize,
    registerDeserializer,
    registerSerializer,
)
from .._eventaccess import EventAccess


__all__ = ()


@unique
class EventAccessJSONKey(Enum):
    """
    Event access JSON keys
    """

    readers = "readers"
    writers = "writers"
    reporters = "reporters"


class EventAccessJSONType(Enum):
    """
    Event access attribute types
    """

    readers = FrozenSet[str]
    writers = FrozenSet[str]
    reporters = FrozenSet[str]


def serializeEventAccess(eventAccess: EventAccess) -> Dict[str, Any]:
    # Map EventAccess attribute names to JSON dict key names
    return dict(
        (key.value, jsonSerialize(getattr(eventAccess, key.name)))
        for key in EventAccessJSONKey
    )


registerSerializer(EventAccess, serializeEventAccess)


def deserializeEventAccess(obj: Dict[str, Any], cl: Type) -> EventAccess:
    assert cl is EventAccess, (cl, obj)

    return cast(
        EventAccess,
        deserialize(obj, EventAccess, EventAccessJSONType, EventAccessJSONKey,),
    )


registerDeserializer(EventAccess, deserializeEventAccess)
