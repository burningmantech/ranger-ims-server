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

from __future__ import absolute_import

"""
JSON bindings for IMS data.

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
            "description: "Large dome, red flags"   // one line (garett,text)
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

__all__ = [
    "json_from_file",
    "json_from_text",
    "json_as_text",

    "datetime_as_rfc3339",
    "rfc3339_as_datetime",

    "JSON",

    "incident_from_json",
    "incident_as_json",
]

from json import dumps, load as json_from_file, loads as json_from_text
from datetime import (
    datetime as DateTime,  # timedelta as TimeDelta, tzinfo as TZInfo
)

from twisted.python.constants import (
    Values, ValueConstant
)

from .tz import utc
from .data import (
    InvalidDataError, IncidentState, Incident, ReportEntry, Ranger,
    Location, TextOnlyAddress, RodGarettAddress,
)

rfc3339_datetime_format = "%Y-%m-%dT%H:%M:%SZ"



def json_as_text(obj):
    """
    Convert an object into JSON text.

    @param obj: An object that is serializable to JSON.
    @type obj: L{object}

    @return: JSON text.
    @rtype: L{unicode}
    """
    return dumps(obj, separators=(',', ':')).decode("UTF-8")



def datetime_as_rfc3339(datetime):
    """
    Convert a date-time object into an RFC 3339 formatted date-time string.

    @param datetime: A non-naive date-time object to convert.
    @type datetime: L{DateTime}

    @return: An RFC 3339 formatted date-time string corresponding to
        C{datetime} (converted to UTC).
    @rtype: L{str}
    """
    if not datetime:
        return None
    else:
        datetime = datetime.astimezone(utc)
        return datetime.strftime(rfc3339_datetime_format)



def rfc3339_as_datetime(rfc3339):
    """
    Convert an RFC 3339 formatted string to a date-time object.

    @param rfc3339: An RFC 3339 formatted string.
    @type rfc3339: L{str}

    @return: An date-time object (in UTC) corresponding to C{rfc3339}.
    @rtype: L{DateTime}
    """
    if not rfc3339:
        return None
    else:
        datetime = DateTime.strptime(rfc3339, rfc3339_datetime_format)
        return datetime.replace(tzinfo=utc)



class JSON(Values):
    # Incident attribute keys
    incident_number   = ValueConstant("number")
    incident_created  = ValueConstant("timestamp")
    incident_priority = ValueConstant("priority")
    incident_state    = ValueConstant("state")
    incident_summary  = ValueConstant("summary")
    incident_location = ValueConstant("location")
    ranger_handles    = ValueConstant("ranger_handles")
    incident_types    = ValueConstant("incident_types")
    report_entries    = ValueConstant("report_entries")

    # Obsolete incident attribute keys
    _location_name    = ValueConstant("location_name")
    _location_address = ValueConstant("location_address")

    # Location attribute subkeys
    location_name = ValueConstant("name")
    location_type = ValueConstant("type")

    # Location type values
    location_type_text   = ValueConstant("text")
    location_type_garett = ValueConstant("garett")

    # Text location type subkeys
    location_text_description = ValueConstant("description")

    # Garett location type subkeys
    location_garett_concentric    = ValueConstant("concentric")
    location_garett_radial_hour   = ValueConstant("radial_hour")
    location_garett_radial_minute = ValueConstant("radial_minute")
    location_garett_description   = ValueConstant("description")

    # State attribute values
    state_new        = ValueConstant("new")
    state_on_hold    = ValueConstant("on_hold")
    state_dispatched = ValueConstant("dispatched")
    state_on_scene   = ValueConstant("on_scene")
    state_closed     = ValueConstant("closed")

    # Obsolete legacy state attribute keys
    _created    = ValueConstant("created")
    _dispatched = ValueConstant("dispatched")
    _on_scene   = ValueConstant("on_scene")
    _closed     = ValueConstant("closed")

    # Ranger attribute keys
    ranger_handle = ValueConstant("handle")
    ranger_name   = ValueConstant("name")
    ranger_status = ValueConstant("status")

    # Report entry attribute keys
    entry_author  = ValueConstant("author")
    entry_text    = ValueConstant("text")
    entry_system  = ValueConstant("system_entry")
    entry_created = ValueConstant("created")

    # Web page reference keys
    page_name = ValueConstant("name")
    page_url  = ValueConstant("url")


    @classmethod
    def describe(cls, value):
        """
        Describe a constant as a human-readable string.

        @param value: A JSON constant.
        @type constant: L{ValueConstant}

        @return: A string description of C{value}.
        @rtype: L{unicode}
        """
        value.name.replace("_", " ").decode("utf-8")



def incident_from_json(root, number, validate=True):
    """
    Create an incident from JSON data.

    @param root: JSON data representing an incident.
    @type root: L{dict}

    @param number: The number of the incident.
        If C{root} specifies an incident number that is different than
        C{number}, raise an L{InvalidDataError}.
    @type number: L{int}

    @param validate: If true, raise L{InvalidDataError} if the data does
        not validate as a fully-well-formed incident.
    @type validate: L{bool}

    @return: The de-serialized incident.
    @rtype: L{Incident}
    """
    if number is None:
        raise TypeError("Incident number may not be null")

    if not isinstance(root, dict):
        raise InvalidDataError("JSON incident must be a dict")

    for attribute in root:
        try:
            JSON.lookupByValue(attribute)
        except Exception:
            raise InvalidDataError("ARGH! Evil Death!")

    json_number = root.get(JSON.incident_number.value, None)

    if json_number is not None:
        if json_number != number:
            raise InvalidDataError(
                "Incident number may not be modified: {0!r} != {1!r}"
                .format(json_number, number)
            )

        root[JSON.incident_number.value] = number

    priority = root.get(JSON.incident_priority.value, None)

    summary = root.get(JSON.incident_summary.value, None)

    location = root.get(JSON.incident_location.value, None)

    if location is None:
        # Try pre-2015 attributes
        location_name = root.get(JSON._location_name.value, None)
        location_address = root.get(JSON._location_address.value, None)

        if location_name is None and location_address is None:
            location = None
        else:
            location = Location(
                name=location_name,
                address=TextOnlyAddress(location_address),
            )
    else:
        location_type = location.get(JSON.location_type.value, None)
        location_name = location.get(JSON.location_name.value, None)

        if location_type == JSON.location_type_text.value:
            location_description = location.get(
                JSON.location_garett_description.value, None
            )

            if location_description is None:
                address = None
            else:
                address = TextOnlyAddress(description=location_description)

        elif location_type == JSON.location_type_garett.value:
            location_concentric = location.get(
                JSON.location_garett_concentric.value, None
            )
            location_hour = location.get(
                JSON.location_garett_radial_hour.value, None
            )
            location_minute = location.get(
                JSON.location_garett_radial_minute.value, None
            )
            location_description = location.get(
                JSON.location_garett_description.value, None
            )

            if (
                location_concentric is None and
                location_hour is None and
                location_minute is None and
                location_description is None
            ):
                address = None
            else:
                address = RodGarettAddress(
                    concentric=location_concentric,
                    radialHour=location_hour,
                    radialMinute=location_minute,
                    description=location_description,
                )

        else:
            raise InvalidDataError(
                "Unknown location type: {}".format(location_type)
            )

        location = Location(name=location_name, address=address)

    ranger_handles = root.get(JSON.ranger_handles.value, None)
    if ranger_handles is None:
        rangers = None
    else:
        rangers = frozenset(
            Ranger(handle, None, None)
            for handle in ranger_handles
        )

    incident_types = root.get(JSON.incident_types.value, None)

    json_entries = root.get(JSON.report_entries.value, None)

    if json_entries is None:
        report_entries = None
    else:
        report_entries = [
            ReportEntry(
                author=entry.get(JSON.entry_author.value, None),
                text=entry.get(JSON.entry_text.value, None),
                created=rfc3339_as_datetime(
                    entry.get(JSON.entry_created.value, None)
                ),
                system_entry=entry.get(JSON.entry_system.value, False),
            )
            for entry in json_entries
        ]

    created = rfc3339_as_datetime(root.get(JSON.incident_created.value, None))

    # 2013 format did not have a true created timestamp, but it did have a
    # created state timestamp, which will have to do
    if created is None:
        created = rfc3339_as_datetime(root.get(JSON._created.value, None))

    json_state = root.get(JSON.incident_state.value, None)

    if json_state is None:
        # Try obsolete attributes
        if root.get(JSON._closed.value, None) is not None:
            state = IncidentState.closed

        elif root.get(JSON._on_scene.value, None) is not None:
            state = IncidentState.on_scene

        elif root.get(JSON._dispatched.value, None) is not None:
            state = IncidentState.dispatched

        elif root.get(JSON._created.value, None) is not None:
            state = IncidentState.new

        else:
            state = None

    else:
        state = IncidentState.lookupByName(json_state)

    incident = Incident(
        number=number,
        priority=priority,
        summary=summary,
        location=location,
        rangers=rangers,
        incident_types=incident_types,
        report_entries=report_entries,
        created=created,
        state=state,
    )

    if validate:
        incident.validate()

    return incident



def incident_as_json(incident):
    """
    Generate JSON data from an incident.

    @param incident: An incident to serialize.
    @type incident: L{Incident}

    @return: C{incident}, serialized as JSON data.
    @rtype: L{dict}
    """

    root = {}

    root[JSON.incident_number.value] = incident.number

    if incident.priority is not None:
        root[JSON.incident_priority.value] = incident.priority

    if incident.summary is not None:
        root[JSON.incident_summary.value] = incident.summary

    if incident.location is not None:
        root[JSON.incident_location.value] = (
            location_as_json(incident.location)
        )

    if incident.rangers is not None:
        root[JSON.ranger_handles.value] = [
            ranger.handle for ranger in incident.rangers
        ]

    if incident.incident_types is not None:
        root[JSON.incident_types.value] = list(incident.incident_types)

    if incident.report_entries is not None:
        root[JSON.report_entries.value] = [
            {
                JSON.entry_author.value: entry.author,
                JSON.entry_text.value: entry.text,
                JSON.entry_created.value: datetime_as_rfc3339(entry.created),
                JSON.entry_system.value: entry.system_entry,
            }
            for entry in incident.report_entries
        ]

    if incident.created is not None:
        root[JSON.incident_created.value] = (
            datetime_as_rfc3339(incident.created)
        )

    if incident.state is not None:
        root[JSON.incident_state.value] = JSON.lookupByName(
            "state_{}".format(incident.state.name)
        ).value

    return root



def ranger_as_json(ranger):
    """
    Generate JSON data from a Ranger.

    @param ranger: A Ranger to serialize.
    @type ranger: L{Ranger}

    @return: C{ranger}, serialized as JSON data.
    @rtype: L{dict}
    """
    return {
        JSON.ranger_handle.value: ranger.handle,
        JSON.ranger_name.value: ranger.name,
        JSON.ranger_status.value: ranger.status,
    }



def location_as_json(location):
    """
    Generate JSON data from a location.

    @param location: A location to serialize.
    @type location: L{Location}

    @return: C{location}, serialized as JSON data.
    @rtype: L{dict}
    """
    if location is None:
        return None

    address = location.address
    if address is None:
        # Location should always have a type
        return {
            JSON.location_name.value: location.name,
            JSON.location_type.value: JSON.location_type_text.value,
            JSON.location_text_description.value: None,
        }
    elif isinstance(address, TextOnlyAddress):
        return {
            JSON.location_name.value: location.name,
            JSON.location_type.value: JSON.location_type_text.value,
            JSON.location_text_description.value: address.description,
        }
    elif isinstance(address, RodGarettAddress):
        return {
            JSON.location_name.value: location.name,
            JSON.location_type.value: JSON.location_type_garett.value,
            JSON.location_garett_concentric.value: address.concentric,
            JSON.location_garett_radial_hour.value: address.radialHour,
            JSON.location_garett_radial_minute.value: address.radialMinute,
            JSON.location_garett_description.value: address.description,
        }
    else:
        raise InvalidDataError("Unknown addresses type: {}".format(address))
