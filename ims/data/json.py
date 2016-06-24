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

from __future__ import absolute_import

__all__ = [
    "jsonFromFile",
    "jsonFromText",
    "textFromJSON",

    "datetimeAsRFC3339",
    "rfc3339AsDateTime",

    "JSON",

    "incidentFromJSON",
    "incidentAsJSON",
    "rangerAsJSON",
    "locationAsJSON",
]

from json import dumps, load as jsonFromFile, loads as jsonFromText, JSONEncoder
from datetime import datetime as DateTime

from twisted.python.constants import (
    Values, ValueConstant
)

from ..tz import utc
from .model import (
    InvalidDataError, IncidentState, Incident, ReportEntry, Ranger,
    Location, TextOnlyAddress, RodGarettAddress,
)

rfc3339_datetime_format = "%Y-%m-%dT%H:%M:%SZ"



class Encoder(JSONEncoder):
    def default(self, obj):
        iterate = getattr(obj, "__iter__", None)
        if iterate is not None:
            return list(iterate())

        return JSONEncoder.default(self, obj)



def textFromJSON(obj, pretty=False):
    """
    Convert an object into JSON text.

    @param obj: An object that is serializable to JSON.
    @type obj: L{object}

    @return: JSON text.
    @rtype: L{unicode}
    """
    if pretty:
        separators = (",", ": ")
        indent = 2
        sort_keys = True
    else:
        separators = (",", ":")
        indent = None
        sort_keys = False

    return dumps(
        obj,
        separators=separators,
        indent=indent,
        sort_keys=sort_keys,
        cls=Encoder,
    ).decode("UTF-8")



def datetimeAsRFC3339(datetime):
    """
    Convert a date-time object into an RFC 3339 formatted date-time string.

    @param datetime: A non-naive date-time object to convert.
    @type datetime: L{DateTime}

    @return: An RFC 3339 formatted date-time string corresponding to
        C{datetime} (converted to UTC).
    @rtype: L{unicode}
    """
    if not datetime:
        return None
    else:
        datetime = datetime.astimezone(utc)
        return datetime.strftime(rfc3339_datetime_format).decode("utf-8")



def rfc3339AsDateTime(rfc3339):
    """
    Convert an RFC 3339 formatted string to a date-time object.

    @param rfc3339: An RFC 3339 formatted string.
    @type rfc3339: L{unicode}

    @return: An date-time object (in UTC) corresponding to C{rfc3339}.
    @rtype: L{DateTime}
    """
    if not rfc3339:
        return None
    else:
        datetime = DateTime.strptime(rfc3339, rfc3339_datetime_format)
        return datetime.replace(tzinfo=utc)



class JSON(Values):
    """
    JSON keys
    """

    # Incident attribute keys
    incident_number   = ValueConstant(u"number")
    incident_created  = ValueConstant(u"timestamp")
    incident_priority = ValueConstant(u"priority")
    incident_state    = ValueConstant(u"state")
    incident_summary  = ValueConstant(u"summary")
    incident_location = ValueConstant(u"location")
    ranger_handles    = ValueConstant(u"ranger_handles")
    incident_types    = ValueConstant(u"incident_types")
    report_entries    = ValueConstant(u"report_entries")

    # Obsolete incident attribute keys
    _location_name    = ValueConstant(u"location_name")
    _location_address = ValueConstant(u"location_address")

    # Location attribute subkeys
    location_name = ValueConstant(u"name")
    location_type = ValueConstant(u"type")

    # Location type values
    location_type_text   = ValueConstant(u"text")
    location_type_garett = ValueConstant(u"garett")

    # Text location type subkeys
    location_text_description = ValueConstant(u"description")

    # Garett location type subkeys
    location_garett_concentric    = ValueConstant(u"concentric")
    location_garett_radial_hour   = ValueConstant(u"radial_hour")
    location_garett_radial_minute = ValueConstant(u"radial_minute")
    location_garett_description   = ValueConstant(u"description")

    # State attribute values
    state_new        = ValueConstant(u"new")
    state_on_hold    = ValueConstant(u"on_hold")
    state_dispatched = ValueConstant(u"dispatched")
    state_on_scene   = ValueConstant(u"on_scene")
    state_closed     = ValueConstant(u"closed")

    # Obsolete legacy state attribute keys
    _created    = ValueConstant(u"created")
    _dispatched = ValueConstant(u"dispatched")
    _on_scene   = ValueConstant(u"on_scene")
    _closed     = ValueConstant(u"closed")

    # Ranger attribute keys
    ranger_handle  = ValueConstant(u"handle")
    ranger_name    = ValueConstant(u"name")
    ranger_status  = ValueConstant(u"status")
    ranger_dms_id  = ValueConstant(u"dms_id")
    ranger_email   = ValueConstant(u"email")
    ranger_on_site = ValueConstant(u"on_site")

    # Report entry attribute keys
    entry_author  = ValueConstant(u"author")
    entry_text    = ValueConstant(u"text")
    entry_system  = ValueConstant(u"system_entry")
    entry_created = ValueConstant(u"created")

    # Web page reference keys
    page_name = ValueConstant(u"name")
    page_url  = ValueConstant(u"url")


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



def incidentFromJSON(root, number, validate=True):
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
    if not isinstance(root, dict):
        raise InvalidDataError("JSON incident must be a dict")

    for attribute in root:
        try:
            JSON.lookupByValue(attribute)
        except Exception:
            raise InvalidDataError(
                "Unknown JSON attribute: {}".format(attribute)
            )

    def verifyType(expectedType, name, value):
        if type(value) is not expectedType:
            raise InvalidDataError(
                "Expected {} for {}, got {!r}"
                .format(expectedType, name, value)
            )

    def get(json, name, expectedType=None, default=None, transform=None):
        value = json.get(name.value, default)

        if value is None:
            return None

        if expectedType is not None:
            verifyType(expectedType, name, value)

        if transform is None:
            return value
        else:
            try:
                return transform(value)
            except (ValueError, TypeError) as e:
                raise InvalidDataError(
                    "Unable to transform {}={!r} with {}: {}"
                    .format(name, value, transform, e)
                )

    json_number = get(root, JSON.incident_number, int)

    if json_number is not None:
        if json_number != number:
            raise InvalidDataError(
                "Incident number may not be modified: {0!r} != {1!r}"
                .format(json_number, number)
            )

        root[JSON.incident_number.value] = number

    priority = get(root, JSON.incident_priority, int)
    summary  = get(root, JSON.incident_summary , unicode)
    location = get(root, JSON.incident_location, dict)

    if location is None:
        # Try pre-2015 attributes
        location_name    = get(root, JSON._location_name   , unicode)
        location_address = get(root, JSON._location_address, unicode)

        if location_name is None and location_address is None:
            location = None
        else:
            location = Location(
                name=location_name,
                address=TextOnlyAddress(location_address),
            )
    else:
        location_type = get(location, JSON.location_type, unicode)
        location_name = get(location, JSON.location_name, unicode)

        if location_type == JSON.location_type_text.value:
            location_description = get(
                location, JSON.location_garett_description, unicode
            )

            if location_description is None:
                address = None
            else:
                address = TextOnlyAddress(description=location_description)

        elif location_type == JSON.location_type_garett.value:
            location_concentric = get(
                location, JSON.location_garett_concentric, int
            )
            location_hour = get(
                location, JSON.location_garett_radial_hour, int
            )
            location_minute = get(
                location, JSON.location_garett_radial_minute, int
            )
            location_description = get(
                location, JSON.location_garett_description, unicode
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

    rangers = get(
        root, JSON.ranger_handles, list,
        transform=(
            lambda handles:
            frozenset(Ranger(handle, None, None) for handle in handles)
        )
    )

    incidentTypes = get(root, JSON.incident_types, list)
    if incidentTypes is not None:
        for incidentType in incidentTypes:
            verifyType(unicode, JSON.incident_types, incidentType)

    json_entries = get(root, JSON.report_entries, list)

    if json_entries is None:
        reportEntries = None
    else:
        reportEntries = [
            ReportEntry(
                author=get(entry, JSON.entry_author, unicode),
                text=get(entry, JSON.entry_text, unicode),
                created=get(
                    entry, JSON.entry_created, unicode,
                    transform=rfc3339AsDateTime,
                ),
                system_entry=get(entry, JSON.entry_system, bool, default=False),
            )
            for entry in json_entries
        ]

    created = get(
        root, JSON.incident_created, unicode, transform=rfc3339AsDateTime
    )

    # 2013 format did not have a true created timestamp, but it did have a
    # created state timestamp, which will have to do
    if created is None:
        created = get(root, JSON._created, unicode, transform=rfc3339AsDateTime)

    json_state = get(root, JSON.incident_state, unicode)

    if json_state is None:
        # Try obsolete attributes
        if get(root, JSON._closed, unicode) is not None:
            state = IncidentState.closed

        elif get(root, JSON._on_scene, unicode) is not None:
            state = IncidentState.on_scene

        elif get(root, JSON._dispatched, unicode) is not None:
            state = IncidentState.dispatched

        elif get(root, JSON._created, unicode) is not None:
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
        incidentTypes=incidentTypes,
        reportEntries=reportEntries,
        created=created,
        state=state,
    )

    if validate:
        incident.validate()

    return incident



def incidentAsJSON(incident):
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
            locationAsJSON(incident.location)
        )

    if incident.rangers is not None:
        root[JSON.ranger_handles.value] = [
            ranger.handle for ranger in incident.rangers
        ]

    if incident.incidentTypes is not None:
        root[JSON.incident_types.value] = list(incident.incidentTypes)

    if incident.reportEntries is not None:
        root[JSON.report_entries.value] = [
            {
                JSON.entry_author.value: entry.author,
                JSON.entry_text.value: entry.text,
                JSON.entry_created.value: datetimeAsRFC3339(entry.created),
                JSON.entry_system.value: entry.system_entry,
            }
            for entry in incident.reportEntries
        ]

    if incident.created is not None:
        root[JSON.incident_created.value] = (
            datetimeAsRFC3339(incident.created)
        )

    if incident.state is not None:
        root[JSON.incident_state.value] = JSON.lookupByName(
            "state_{}".format(incident.state.name)
        ).value

    return root



def rangerAsJSON(ranger):
    """
    Generate JSON data from a Ranger.

    @param ranger: A Ranger to serialize.
    @type ranger: L{Ranger}

    @return: C{ranger}, serialized as JSON data.
    @rtype: L{dict}
    """
    return {
        JSON.ranger_handle.value  : ranger.handle,
        JSON.ranger_name.value    : ranger.name,
        JSON.ranger_status.value  : ranger.status,
        JSON.ranger_dms_id.value  : ranger.dmsID,
        JSON.ranger_email.value   : ranger.email,
        JSON.ranger_on_site.value : ranger.onSite,
    }



def locationAsJSON(location):
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
