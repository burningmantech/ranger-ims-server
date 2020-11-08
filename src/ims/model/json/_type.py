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
JSON serialization/deserialization for incident type
"""


from enum import Enum, unique
from typing import Any, Dict, Type, cast

from ._json import (
    deserialize,
    jsonSerialize,
    registerDeserializer,
    registerSerializer,
)
from .._type import IncidentType


__all__ = ()


@unique
class IncidentTypeJSONKey(Enum):
    """
    Incident type JSON keys
    """

    name = "name"
    hidden = "hidden"


class IncidentTypeJSONType(Enum):
    """
    Incident type attribute types
    """

    name = str  # type: ignore[assignment]
    hidden = bool


def serializeIncidentType(incidentType: IncidentType) -> Dict[str, Any]:
    # Map IncidentType attribute names to JSON dict key names
    return {
        key.value: jsonSerialize(getattr(incidentType, key.name))
        for key in IncidentTypeJSONKey
    }


registerSerializer(IncidentType, serializeIncidentType)


def deserializeIncidentType(
    obj: Dict[str, Any], cl: Type[IncidentType]
) -> IncidentType:
    assert cl is IncidentType, (cl, obj)

    return cast(
        IncidentType,
        deserialize(
            obj, IncidentType, IncidentTypeJSONType, IncidentTypeJSONKey
        ),
    )


registerDeserializer(IncidentType, deserializeIncidentType)


# Nothing to register for KnownIncidentType; by default, cattrs handles enums
# by value, which is what we want here.
