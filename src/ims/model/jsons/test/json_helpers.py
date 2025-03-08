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
Expected JSON encoding for model data.
"""

from typing import Any, cast

from ..._address import Address, RodGarettAddress, TextOnlyAddress
from ..._entry import ReportEntry
from ..._event import Event
from ..._eventaccess import EventAccess
from ..._eventdata import EventData
from ..._imsdata import IMSData
from ..._incident import Incident
from ..._location import Location
from ..._priority import IncidentPriority
from ..._ranger import Ranger, RangerStatus
from ..._report import FieldReport
from ..._state import IncidentState
from ..._type import IncidentType, KnownIncidentType
from .._json import jsonSerialize


__all__ = ()


##
# Address
##


def jsonFromAddress(address: Address) -> dict[str, Any]:
    if isinstance(address, TextOnlyAddress):
        return jsonFromTextOnlyAddress(address)

    if isinstance(address, RodGarettAddress):
        return jsonFromRodGarettAddress(address)

    raise TypeError(f"Unknown address type {address!r}")


def jsonFromTextOnlyAddress(address: TextOnlyAddress) -> dict[str, Any]:
    return {"type": "text", "description": jsonSerialize(address.description)}


def jsonFromRodGarettAddress(address: RodGarettAddress) -> dict[str, Any]:
    return {
        "type": "garett",
        "concentric": jsonSerialize(address.concentric),
        "radial_hour": jsonSerialize(address.radialHour),
        "radial_minute": jsonSerialize(address.radialMinute),
        "description": jsonSerialize(address.description),
    }


##
# Entry
##


def jsonFromReportEntry(entry: ReportEntry) -> dict[str, Any]:
    return {
        "id": jsonSerialize(entry.id),
        "created": jsonSerialize(entry.created),
        "author": jsonSerialize(entry.author),
        "system_entry": jsonSerialize(entry.automatic),
        "text": jsonSerialize(entry.text),
        "stricken": jsonSerialize(entry.stricken),
        "has_attachment": bool(entry.attachedFile),
    }


##
# Event
##


def jsonFromEvent(event: Event) -> dict[str, str]:
    return {"id": event.id, "name": event.id}


def jsonFromEventAccess(eventAccess: EventAccess) -> dict[str, list[str]]:
    return {
        "readers": cast(list[str], jsonSerialize(eventAccess.readers)),
        "writers": cast(list[str], jsonSerialize(eventAccess.writers)),
        "reporters": cast(list[str], jsonSerialize(eventAccess.reporters)),
    }


def jsonFromEventData(eventData: EventData) -> dict[str, Any]:
    return {
        "event": jsonSerialize(eventData.event),
        "access": jsonSerialize(eventData.access),
        "concentric_streets": jsonSerialize(eventData.concentricStreets),
        "incidents": [jsonSerialize(i) for i in eventData.incidents],
        "field_reports": [jsonSerialize(r) for r in eventData.fieldReports],
    }


def jsonFromIMSData(imsData: IMSData) -> dict[str, Any]:
    return {
        "events": [jsonSerialize(e) for e in imsData.events],
        "incident_types": [jsonSerialize(t) for t in imsData.incidentTypes],
    }


##
# Incident
##


def jsonFromIncident(incident: Incident) -> dict[str, Any]:
    return {
        "event": jsonSerialize(incident.eventID),
        "number": jsonSerialize(incident.number),
        "created": jsonSerialize(incident.created),
        "last_modified": jsonSerialize(incident.lastModified),
        "state": jsonSerialize(incident.state),
        "priority": jsonSerialize(incident.priority),
        "summary": jsonSerialize(incident.summary),
        "location": jsonSerialize(incident.location),
        "ranger_handles": [jsonSerialize(r) for r in incident.rangerHandles],
        "incident_types": [jsonSerialize(t) for t in incident.incidentTypes],
        "report_entries": [jsonSerialize(e) for e in sorted(incident.reportEntries)],
        "field_reports": [
            jsonSerialize(n) for n in sorted(incident.fieldReportNumbers)
        ],
    }


##
# Location
##


def jsonFromLocation(location: Location) -> dict[str, Any]:
    json = {"name": location.name}

    addressJSON = jsonFromAddress(location.address)
    json.update(addressJSON)

    return json


##
# Priority
##


def jsonFromIncidentPriority(priority: IncidentPriority) -> int:
    return {
        IncidentPriority.high: 1,
        IncidentPriority.normal: 3,
        IncidentPriority.low: 5,
    }[priority]


##
# Ranger
##


def jsonFromRangerStatus(status: RangerStatus) -> str:
    return {
        RangerStatus.active: "active",
        RangerStatus.inactive: "inactive",
        RangerStatus.inactiveExtension: "inactiveExtension",
        RangerStatus.other: "(unknown)",
    }[status]


def jsonFromRanger(ranger: Ranger) -> dict[str, Any]:
    return {
        "handle": ranger.handle,
        "status": jsonFromRangerStatus(ranger.status),
        # email is intentionally not serialized
        "onsite": ranger.onsite,
        "directory_id": ranger.directoryID,
        # password is intentionally not serialized
    }


##
# Report
##


def jsonFromFieldReport(report: FieldReport) -> dict[str, Any]:
    return {
        "event": jsonSerialize(report.eventID),
        "number": jsonSerialize(report.number),
        "created": jsonSerialize(report.created),
        "summary": jsonSerialize(report.summary),
        "incident": jsonSerialize(report.incidentNumber),
        "report_entries": [jsonSerialize(e) for e in report.reportEntries],
    }


##
# State
##


def jsonFromIncidentState(state: IncidentState) -> str:
    return {
        IncidentState.new: "new",
        IncidentState.onHold: "on_hold",
        IncidentState.dispatched: "dispatched",
        IncidentState.onScene: "on_scene",
        IncidentState.closed: "closed",
    }[state]


##
# Type
##


def jsonFromIncidentType(incidentType: IncidentType) -> dict[str, Any]:
    return {
        "name": jsonSerialize(incidentType.name),
        "hidden": jsonSerialize(incidentType.hidden),
    }


def jsonFromKnownIncidentType(incidentType: KnownIncidentType) -> str:
    return incidentType.value
