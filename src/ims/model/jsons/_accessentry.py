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
JSON serialization/deserialization for access entry
"""

from enum import Enum, unique
from typing import Any, cast

from .._accessentry import AccessEntry
from .._accessvalidity import AccessValidity
from ._json import (
    deserialize,
    jsonSerialize,
    registerDeserializer,
    registerSerializer,
)


__all__ = ()


@unique
class AccessEntryJSONKey(Enum):
    """
    Access entry JSON keys
    """

    expression = "expression"
    validity = "validity"


class AccessEntryJSONType(Enum):
    """
    Access entry attribute types
    """

    expression = str
    validity = AccessValidity


def serializeAccessEntry(accessEntry: AccessEntry) -> dict[str, Any]:
    # Map AccessEntry attribute names to JSON dict key names
    return {
        key.value: jsonSerialize(getattr(accessEntry, key.name))
        for key in AccessEntryJSONKey
    }


registerSerializer(AccessEntry, serializeAccessEntry)


def deserializeAccessEntry(obj: dict[str, Any], cl: type[AccessEntry]) -> AccessEntry:
    assert cl is AccessEntry, (cl, obj)

    return cast(
        "AccessEntry",
        deserialize(
            obj,
            AccessEntry,
            AccessEntryJSONType,
            AccessEntryJSONKey,
        ),
    )


registerDeserializer(AccessEntry, deserializeAccessEntry)
