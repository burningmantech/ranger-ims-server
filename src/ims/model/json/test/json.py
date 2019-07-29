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

from typing import Any, Dict, List

from .._json import jsonSerialize
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
from ..._report import IncidentReport
from ..._state import IncidentState
from ..._type import IncidentType, KnownIncidentType


__all__ = ()


##
# Address
##

def jsonFromAddress(address: Address) -> Dict[str, Any]:
    if isinstance(address, TextOnlyAddress):
        return jsonFromTextOnlyAddress(address)
    elif isinstance(address, RodGarettAddress):
        return jsonFromRodGarettAddress(address)
    else:
        raise TypeError(
            f"Unknown address type {address!r}"
        )


def jsonFromTextOnlyAddress(address: TextOnlyAddress) -> Dict[str, Any]:
    return dict(type="text", description=jsonSerialize(address.description))


def jsonFromRodGarettAddress(address: RodGarettAddress) -> Dict[str, Any]:
    return dict(
        type="garett",
        concentric=jsonSerialize(address.concentric),
        radial_hour=jsonSerialize(address.radialHour),
        radial_minute=jsonSerialize(address.radialMinute),
        description=jsonSerialize(address.description),
    )


##
# Entry
##

def jsonFromReportEntry(entry: ReportEntry) -> Dict[str, Any]:
    return dict(
        created=jsonSerialize(entry.created),
        author=jsonSerialize(entry.author),
        system_entry=jsonSerialize(entry.automatic),
        text=jsonSerialize(entry.text),
    )


##
# Event
##

def jsonFromEvent(event: Event) -> str:
    return event.id


def jsonFromEventAccess(eventAccess: EventAccess) -> Dict[str, List[str]]:
    return dict(
        readers=jsonSerialize(eventAccess.readers),
        writers=jsonSerialize(eventAccess.writers),
        reporters=jsonSerialize(eventAccess.reporters),
    )


def jsonFromEventData(eventData: EventData) -> Dict[str, Any]:
    return dict(
        event=jsonSerialize(eventData.event),
        access=jsonSerialize(eventData.access),
        concentric_streets=eventData.concentricStreets,
        incidents=[jsonSerialize(i) for i in eventData.incidents],
        incident_reports=[jsonSerialize(r) for r in eventData.incidentReports],
    )


def jsonFromIMSData(imsData: IMSData) -> Dict[str, Any]:
    return dict(
        events=[jsonSerialize(e) for e in imsData.events],
        incident_types=[jsonSerialize(t) for t in imsData.incidentTypes],
    )


##
# Incident
##

def jsonFromIncident(incident: Incident) -> Dict[str, Any]:
    return dict(
        event=jsonSerialize(incident.event),
        number=jsonSerialize(incident.number),
        created=jsonSerialize(incident.created),
        state=jsonSerialize(incident.state),
        priority=jsonSerialize(incident.priority),
        summary=jsonSerialize(incident.summary),
        location=jsonSerialize(incident.location),
        ranger_handles=frozenset(
            jsonSerialize(r) for r in incident.rangerHandles
        ),
        incident_types=frozenset(
            jsonSerialize(t) for t in incident.incidentTypes
        ),
        report_entries=tuple(
            jsonSerialize(e) for e in sorted(incident.reportEntries)
        ),
        incident_reports=frozenset(
            jsonSerialize(n) for n in sorted(incident.incidentReportNumbers)
        ),
    )


##
# Location
##

def jsonFromLocation(location: Location) -> Dict[str, Any]:
    json = dict(name=location.name)

    addressJSON = jsonFromAddress(location.address)
    json.update(addressJSON)

    return json


##
# Priority
##

def jsonFromIncidentPriority(priority: IncidentPriority) -> int:
    return {
        IncidentPriority.high:   1,
        IncidentPriority.normal: 3,
        IncidentPriority.low:    5,
    }[priority]


##
# Ranger
##

def jsonFromRangerStatus(status: RangerStatus) -> str:
    return {
        RangerStatus.prospective: "prospective",
        RangerStatus.alpha:       "alpha",
        RangerStatus.bonked:      "bonked",
        RangerStatus.active:      "active",
        RangerStatus.inactive:    "inactive",
        RangerStatus.retired:     "retired",
        RangerStatus.uberbonked:  "uberbonked",
        RangerStatus.vintage:     "vintage",
        RangerStatus.deceased:    "deceased",
        RangerStatus.other:       "(unknown)",
    }[status]


def jsonFromRanger(ranger: Ranger) -> Dict[str, Any]:
    return dict(
        handle=ranger.handle,
        name=ranger.name,
        status=jsonFromRangerStatus(ranger.status),
        dms_id=ranger.dmsID,
        email=ranger.email,
        on_site=ranger.onSite,
    )


##
# Report
##

def jsonFromIncidentReport(report: IncidentReport) -> Dict[str, Any]:
    return dict(
        event=jsonSerialize(report.event),
        number=jsonSerialize(report.number),
        created=jsonSerialize(report.created),
        summary=jsonSerialize(report.summary),
        incident=jsonSerialize(report.incidentNumber),
        report_entries=tuple(jsonSerialize(e) for e in report.reportEntries),
    )


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

def jsonFromIncidentType(incidentType: IncidentType) -> Dict[str, Any]:
    return dict(
        name=jsonSerialize(incidentType.name),
        hidden=jsonSerialize(incidentType.hidden),
    )


def jsonFromKnownIncidentType(incidentType: KnownIncidentType) -> str:
    return incidentType.value
