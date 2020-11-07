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
JSON serialization/deserialization for event data
"""

from enum import Enum, unique
from typing import Any, Dict, List, Type, cast

from ._json import (
    deserialize,
    jsonSerialize,
    registerDeserializer,
    registerSerializer,
)
from .._event import Event
from .._eventaccess import EventAccess
from .._eventdata import EventData
from .._incident import Incident
from .._report import IncidentReport


__all__ = ()


@unique
class EventDataJSONKey(Enum):
    """
    Event data JSON keys
    """

    event = "event"
    access = "access"
    concentricStreets = "concentric_streets"
    incidents = "incidents"
    incidentReports = "incident_reports"


class EventDataJSONType(Enum):
    """
    Event data attribute types
    """

    event = Event
    access = EventAccess
    concentricStreets = Dict[str, str]
    incidents = List[Incident]
    incidentReports = List[IncidentReport]


def serializeEventData(eventData: EventData) -> Dict[str, Any]:
    # Map event data attribute names to JSON dict key names
    return dict(
        (key.value, jsonSerialize(getattr(eventData, key.name)))
        for key in EventDataJSONKey
    )


registerSerializer(EventData, serializeEventData)


def deserializeEventData(obj: Dict[str, Any], cl: Type[EventData]) -> EventData:
    assert cl is EventData, (cl, obj)

    return cast(
        EventData,
        deserialize(
            obj,
            EventData,
            EventDataJSONType,
            EventDataJSONKey,
        ),
    )


registerDeserializer(EventData, deserializeEventData)
