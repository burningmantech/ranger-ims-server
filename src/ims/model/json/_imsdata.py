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
JSON serialization/deserialization for IMS data
"""

from enum import Enum, unique
from typing import Any, cast

from .._eventdata import EventData
from .._imsdata import IMSData
from .._type import IncidentType
from ._json import (
    deserialize,
    jsonSerialize,
    registerDeserializer,
    registerSerializer,
)


__all__ = ()


@unique
class IMSDataJSONKey(Enum):
    """
    Event data JSON keys
    """

    events = "events"
    incidentTypes = "incident_types"


class IMSDataJSONType(Enum):
    """
    Event data attribute types
    """

    events = frozenset[EventData]
    incidentTypes = frozenset[IncidentType]


def serializeIMSData(imsData: IMSData) -> dict[str, Any]:
    # Map event data attribute names to JSON dict key names
    return {
        key.value: jsonSerialize(getattr(imsData, key.name))
        for key in IMSDataJSONKey
    }


registerSerializer(IMSData, serializeIMSData)


def deserializeIMSData(obj: dict[str, Any], cl: type[IMSData]) -> IMSData:
    assert cl is IMSData, (cl, obj)

    return cast(
        IMSData,
        deserialize(
            obj,
            IMSData,
            IMSDataJSONType,
            IMSDataJSONKey,
        ),
    )


registerDeserializer(IMSData, deserializeIMSData)
