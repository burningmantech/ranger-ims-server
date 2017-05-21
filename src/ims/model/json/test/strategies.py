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
Test strategies for model data.
"""

from typing import Callable

from hypothesis.extra.datetime import datetimes
from hypothesis.strategies import (
    booleans, composite, integers, iterables, none, one_of as oneOf,
    sampled_from as sampledFrom, text,
)

from ..._address import Address, RodGarettAddress, TextOnlyAddress
from ..._entry import ReportEntry
from ..._event import Event
from ..._incident import Incident
from ..._location import Location
from ..._priority import IncidentPriority
from ..._report import IncidentReport
from ..._state import IncidentState
from ..._type import IncidentType


__all__ = ()


##
# Address
##

@composite
def textOnlyAddresses(draw: Callable) -> TextOnlyAddress:
    description = draw(text())

    return TextOnlyAddress(description=description)


@composite
def rodGarettAddresses(draw: Callable) -> RodGarettAddress:
    return RodGarettAddress(
        concentric=draw(integers(min_value=0, max_value=12)),
        radialHour=draw(integers(min_value=1, max_value=12)),
        radialMinute=draw(integers(min_value=0, max_value=59)),
        description=draw(text()),
    )


@composite
def addresses(draw: Callable) -> Address:
    return draw(oneOf((textOnlyAddresses(), rodGarettAddresses())))


##
# Entry
##

@composite
def reportEntries(draw: Callable) -> ReportEntry:
    return ReportEntry(
        created=draw(datetimes()),
        author=draw(text(min_size=1)),
        automatic=draw(booleans()),
        text=draw(text(min_size=1)),
    )


##
# Event
##

@composite
def events(draw: Callable) -> Event:
    return Event(id=draw(text(min_size=1)))


##
# Incident
##

@composite
def incidentSummaries(draw: Callable) -> str:
    return draw(oneOf(none(), text()))


@composite
def incidents(draw: Callable) -> Incident:
    return Incident(
        event=draw(events()),
        number=draw(integers(min_value=1)),
        created=draw(datetimes()),
        state=draw(incidentStates()),
        priority=draw(incidentPriorities()),
        summary=draw(incidentSummaries()),
        location=draw(locations()),
        rangers=draw(iterables(rangerHandles())),
        incidentTypes=draw(iterables(incidentTypesText())),
        reportEntries=draw(iterables(reportEntries())),
    )


##
# Location
##

@composite
def locations(draw: Callable) -> Location:
    return Location(name=draw(text()), address=draw(addresses()))


##
# Priority
##

@composite
def incidentPriorities(draw: Callable) -> IncidentPriority:
    return draw(sampledFrom(IncidentPriority))


##
# Ranger
##

@composite
def rangerHandles(draw: Callable) -> str:
    return draw(text(min_size=1))


##
# Report
##

@composite
def incidentReports(draw: Callable) -> IncidentReport:
    return IncidentReport(
        number=draw(integers(min_value=1)),
        created=draw(datetimes()),
        summary=draw(text(min_size=1)),
        reportEntries=sorted(draw(iterables(reportEntries()))),
    )


##
# State
##

@composite
def incidentStates(draw: Callable) -> IncidentState:
    return draw(sampledFrom(IncidentState))


##
# Type
##

@composite
def incidentTypesText(draw: Callable) -> str:
    return draw(text(min_size=1))


@composite
def incidentTypes(draw: Callable) -> IncidentType:
    return draw(sampledFrom(IncidentType))
