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
JSON serialization/deserialization for incidents
"""

from datetime import datetime as DateTime
from enum import Enum, unique
from typing import Any, cast

from .._entry import ReportEntry
from .._incident import Incident
from .._location import Location
from .._priority import IncidentPriority
from .._state import IncidentState
from ._json import (
    deserialize,
    jsonSerialize,
    registerDeserializer,
    registerSerializer,
)


__all__ = ()


@unique
class IncidentJSONKey(Enum):
    """
    Incident JSON keys
    """

    eventID = "event"
    number = "number"
    created = "created"
    state = "state"
    priority = "priority"
    summary = "summary"
    location = "location"
    rangerHandles = "ranger_handles"
    incidentTypes = "incident_types"
    reportEntries = "report_entries"
    incidentReportNumbers = "incident_reports"


class IncidentJSONType(Enum):
    """
    Incident attribute types
    """

    eventID = str
    number = int
    created = DateTime
    state = IncidentState
    priority = IncidentPriority
    summary = str | None
    location = Location
    rangerHandles = set[str]
    incidentTypes = set[str]
    reportEntries = list[ReportEntry]
    incidentReportNumbers = set[int]


def serializeIncident(incident: Incident) -> dict[str, Any]:
    # Map Incident attribute names to JSON dict key names
    return {
        key.value: jsonSerialize(getattr(incident, key.name)) for key in IncidentJSONKey
    }


registerSerializer(Incident, serializeIncident)


def deserializeIncident(obj: dict[str, Any], cl: type[Incident]) -> Incident:
    assert cl is Incident, (cl, obj)

    return cast(
        Incident,
        deserialize(
            obj,
            Incident,
            IncidentJSONType,
            IncidentJSONKey,
        ),
    )


registerDeserializer(Incident, deserializeIncident)
