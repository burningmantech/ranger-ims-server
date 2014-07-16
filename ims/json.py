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
JSON bindings for IMS data
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
from datetime import datetime as DateTime

from twisted.python.constants import (
    Values, ValueConstant
)

from .data import (
    InvalidDataError, IncidentState, Incident, ReportEntry, Ranger, Location
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
    if not datetime:
        return None
    else:
        return datetime.strftime(rfc3339_datetime_format)



def rfc3339_as_datetime(rfc3339):
    if not rfc3339:
        return None
    else:
        return DateTime.strptime(rfc3339, rfc3339_datetime_format)



class JSON(Values):
    # Incident attribute keys
    number           = ValueConstant("number")
    priority         = ValueConstant("priority")
    summary          = ValueConstant("summary")
    location_name    = ValueConstant("location_name")
    location_address = ValueConstant("location_address")
    ranger_handles   = ValueConstant("ranger_handles")
    incident_types   = ValueConstant("incident_types")
    report_entries   = ValueConstant("report_entries")
    author           = ValueConstant("author")
    text             = ValueConstant("text")
    system_entry     = ValueConstant("system_entry")
    created          = ValueConstant("created")
    state            = ValueConstant("state")
    state_created    = ValueConstant("created")
    state_dispatched = ValueConstant("dispatched")
    state_on_scene   = ValueConstant("on_scene")
    state_closed     = ValueConstant("closed")
    name             = ValueConstant("name")
    url              = ValueConstant("url")

    # Ranger attribute keys
    ranger_handle = ValueConstant("handle")
    ranger_name   = ValueConstant("name")
    ranger_status = ValueConstant("status")


    @classmethod
    def describe(cls, value):
        """
        Describe a constant as a human-readable string.

        @param value: A JSON constant.
        @type constant: L{ValueConstant}

        @return: A string description of C{value}.
        @rtype: L{unicode}
        """
        return {
            cls.created: u"new",
        }.get(value, value.name.replace("_", " ").decode("utf-8"))



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

    for attribute in root:
        try:
            JSON.lookupByValue(attribute)
        except Exception:
            raise RuntimeError("ARGH! Evil Death!")

    json_number = root.get(JSON.number.value, None)

    if json_number is not None:
        if json_number != number:
            raise InvalidDataError(
                "Incident number may not be modified: {0!r} != {1!r}"
                .format(json_number, number)
            )

        root[JSON.number.value] = number

    if type(root) is not dict:
        raise InvalidDataError("JSON incident must be a dict")

    location_name = root.get(JSON.location_name.value, None)
    location_address = root.get(JSON.location_address.value, None)

    if location_name is None and location_address is None:
        location = None
    else:
        location = Location(name=location_name, address=location_address)

    ranger_handles = root.get(JSON.ranger_handles.value, None)
    if ranger_handles is None:
        rangers = None
    else:
        rangers = [
            Ranger(handle, None, None)
            for handle in ranger_handles
        ]

    json_entries = root.get(JSON.report_entries.value, None)

    if json_entries is None:
        report_entries = None
    else:
        report_entries = [
            ReportEntry(
                author=entry.get(JSON.author.value, u"<unknown>"),
                text=entry.get(JSON.text.value, None),
                created=rfc3339_as_datetime(
                    entry.get(JSON.created.value, None)
                ),
                system_entry=entry.get(JSON.system_entry.value, False),
            )
            for entry in json_entries
        ]

    json_state = root.get(JSON.state.value, None)

    if json_state is None:
        state = None
    else:
        state = IncidentState.lookupByName(json_state)

    incident = Incident(
        number=number,
        priority=root.get(JSON.priority.value, None),
        summary=root.get(JSON.summary.value, None),
        location=location,
        rangers=rangers,
        incident_types=root.get(JSON.incident_types.value, None),
        report_entries=report_entries,
        created=rfc3339_as_datetime(root.get(JSON.created.value, None)),
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

    root[JSON.number.value] = incident.number

    if incident.priority is not None:
        root[JSON.priority.value] = incident.priority

    if incident.summary is not None:
        root[JSON.summary.value] = incident.summary

    if incident.location is not None:
        root[JSON.location_name.value] = incident.location.name
        root[JSON.location_address.value] = incident.location.address

    if incident.rangers is not None:
        root[JSON.ranger_handles.value] = [
            ranger.handle for ranger in incident.rangers
        ]

    if incident.incident_types is not None:
        root[JSON.incident_types.value] = tuple(incident.incident_types)

    if incident.report_entries is not None:
        root[JSON.report_entries.value] = [
            {
                JSON.author.value: entry.author,
                JSON.text.value: entry.text,
                JSON.created.value: datetime_as_rfc3339(entry.created),
                JSON.system_entry.value: entry.system_entry,
            }
            for entry in incident.report_entries
        ]

    if incident.created is not None:
        root[JSON.created.value] = datetime_as_rfc3339(incident.created)

    if incident.state is not None:
        root[JSON.state.value] = JSON.lookupByName(
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
        "handle": ranger.handle,
        "name": ranger.name,
        "status": ranger.status,
    }
