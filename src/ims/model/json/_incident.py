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

r"""
JSON serialization/deserialization for incidents

2017 JSON incident schema makes location.concentric a string and renames the
timestamp key on incident to created.
    {
        "number": 101,                              // int >= 0
        "priority": 3,                              // int {1,3,5}
        "summary": "Diapers, please",               // one line
        "location": {
            "name": "Camp Fishes",                  // one line
            "type": "garett",                       // {"text","garett"}
            "concentric": "11",                     // string ID
            "radial_hour": 8,                       // int 2-10 (garett)
            "radial_minute": 15,                    // int 0-59 (garett)
            "description": "Large dome, red flags"  // one line (garett,text)
        }
        "ranger_handles": [
            "Santa Cruz"                            // handle in Clubhouse
        ],
        "incident_types": [
            "Law Enforcement"                       // from list in config
        ],
        "report_entries": [
            {
                "author": "Hot Yogi",               // handle in Clubhouse
                "created": "2014-08-30T21:12:50Z",  // RFC 3339, Zulu
                "system_entry": false,              // boolean
                "text": "Need diapers\nPronto"      // multi-line
            }
        ],
        "timestamp": "2014-08-30T21:38:11Z"         // RFC 3339, Zulu
        "state": "closed",                          // from JSON.state_*
    }

2015 JSON incident schema replaces top-level location attributes with a
dictionary.
    {
        "number": 101,                              // int >= 0
        "priority": 3,                              // int {1,3,5}
        "summary": "Diapers, please",               // one line
        "location": {
            "name": "Camp Fishes",                  // one line
            "type": "garett",                       // {"text","garett"}
            "concentric": 11,                       // int >= 0 (garett)
            "radial_hour": 8,                       // int 2-10 (garett)
            "radial_minute": 15,                    // int 0-59 (garett)
            "description": "Large dome, red flags"  // one line (garett,text)
        }
        "ranger_handles": [
            "Santa Cruz"                            // handle in Clubhouse
        ],
        "incident_types": [
            "Law Enforcement"                       // from list in config
        ],
        "report_entries": [
            {
                "author": "Hot Yogi",               // handle in Clubhouse
                "created": "2014-08-30T21:12:50Z",  // RFC 3339, Zulu
                "system_entry": false,              // boolean
                "text": "Need diapers\nPronto"      // multi-line
            }
        ],
        "timestamp": "2014-08-30T21:38:11Z"         // RFC 3339, Zulu
        "state": "closed",                          // from JSON.state_*
    }

2014 JSON incident schema replaces per-state time stamp attributes with a
created time stamp plus a state attribute:
    {
        "number": 101,                              // int >= 0
        "priority": 3,                              // {1,3,5}
        "summary": "Diapers, please",               // one line
        "location_address": "8:15 & K",             // one line
        "location_name": "Camp Fishes",             // one line
        "ranger_handles": [
            "Santa Cruz"                            // handle in Clubhouse
        ],
        "incident_types": [
            "Law Enforcement"                       // from list in config
        ],
        "report_entries": [
            {
                "author": "Hot Yogi",               // handle in Clubhouse
                "created": "2014-08-30T21:12:50Z",  // RFC 3339, Zulu
                "system_entry": false,              // boolean
                "text": "Need diapers\nPronto"      // multi-line
            }
        ],
        "timestamp": "2014-08-30T21:38:11Z"         // RFC 3339, Zulu
        "state": "closed",                          // from JSON.state_*
    }

2013 JSON incident schema:
    {
        "number": 101,                              // int >= 0
        "priority": 3,                              // {1,2,3,4,5}
        "summary": "Diapers, please",               // one line
        "location_address": "8:15 & K",             // one line
        "location_name": "Camp Fishes",             // one line
        "ranger_handles": [
            "Santa Cruz"                            // handle in Clubhouse
        ],
        "incident_types": [
            "Law Enforcement"                       // from list in config
        ],
        "report_entries": [
            {
                "author": "Hot Yogi",               // handle in Clubhouse
                "created": "2014-08-30T21:12:50Z",  // RFC 3339, Zulu
                "system_entry": false,              // boolean
                "text": "Need diapers\nPronto"      // multi-line
            }
        ],
        "created": "2014-08-30T21:38:11Z"           // RFC 3339, Zulu
        "dispatched": "2014-08-30T21:39:42Z"        // RFC 3339, Zulu
        "on_scene": "2014-08-30T21:45:53Z"          // RFC 3339, Zulu
        "closed": "2014-08-30T21:58:01Z"            // RFC 3339, Zulu
    }
"""

from datetime import datetime as DateTime
from enum import Enum, unique
from typing import Any, Dict, List, Optional, Set, Type

from ._json import (
    deserialize, jsonSerialize, registerDeserializer, registerSerializer
)
from .._entry import ReportEntry
from .._event import Event
from .._incident import Incident
from .._location import Location
from .._priority import IncidentPriority
from .._state import IncidentState


__all__ = ()



@unique
class IncidentJSONKey(Enum):
    """
    Incident JSON keys
    """

    event         = "event"
    number        = "number"
    created       = "created"
    state         = "state"
    priority      = "priority"
    summary       = "summary"
    location      = "location"
    rangerHandles = "ranger_handles"
    incidentTypes = "incident_types"
    reportEntries = "report_entries"



class IncidentJSONType(Enum):
    """
    Incident attribute types
    """

    event         = Event
    number        = int
    created       = DateTime
    state         = IncidentState
    priority      = IncidentPriority
    summary       = Optional[str]
    location      = Location
    rangerHandles = Set[str]
    incidentTypes = Set[str]
    reportEntries = List[ReportEntry]



def serializeIncident(incident: Incident) -> Dict[str, Any]:
    # Map Incident attribute names to JSON dict key names
    return dict(
        (key.value, jsonSerialize(getattr(incident, key.name)))
        for key in IncidentJSONKey
    )

registerSerializer(Incident, serializeIncident)


def deserializeIncident(obj: Dict[str, Any], cl: Type) -> Incident:
    assert cl is Incident, (cl, obj)

    return deserialize(
        obj, Incident, IncidentJSONType, IncidentJSONKey,
    )

registerDeserializer(Incident, deserializeIncident)
