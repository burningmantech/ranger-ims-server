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

from typing import Any, Dict

from .._json import jsonSerialize
from ..._address import RodGarettAddress, TextOnlyAddress
from ..._entry import ReportEntry
from ..._event import Event
from ..._location import Location
from ..._priority import IncidentPriority
from ..._report import IncidentReport
from ..._state import IncidentState
from ..._type import IncidentType


__all__ = ()


##
# Address
##

def jsonFromTextOnlyAddress(address: TextOnlyAddress) -> Dict[str, Any]:
    return dict(description=jsonSerialize(address.description))


def jsonFromRodGarettAddress(address: RodGarettAddress) -> Dict[str, Any]:
    return dict(
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


##
# Location
##

def jsonFromLocation(location: Location) -> Dict[str, Any]:
    return dict(
        name=jsonSerialize(location.name),
        address=jsonSerialize(location.address),
    )


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
# Report
##

def jsonFromIncidentReport(report: IncidentReport) -> Dict[str, Any]:
    return dict(
        number=jsonSerialize(report.number),
        created=jsonSerialize(report.created),
        summary=jsonSerialize(report.summary),
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

def jsonFromIncidentType(incidentType: IncidentType) -> str:
    return incidentType.value
