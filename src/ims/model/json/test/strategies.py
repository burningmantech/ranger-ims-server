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
    booleans, choices, composite, integers, one_of as oneOf,
    sampled_from as sampledFrom, text,
)

from ..._address import Address, RodGarettAddress, TextOnlyAddress
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

@composite
def textOnlyAddresses(draw: Callable) -> TextOnlyAddress:
    description = draw(text())

    return TextOnlyAddress(description=description)


@composite
def rodGarettAddresses(draw: Callable) -> RodGarettAddress:
    concentric   = draw(integers(min_value=0, max_value=12))
    radialHour   = draw(integers(min_value=1, max_value=12))
    radialMinute = draw(integers(min_value=0, max_value=59))
    description  = draw(text())

    return RodGarettAddress(
        concentric=concentric,
        radialHour=radialHour,
        radialMinute=radialMinute,
        description=description,
    )


@composite
def addresses(draw: Callable) -> Address:
    return draw(oneOf((textOnlyAddresses(), rodGarettAddresses())))


##
# Entry
##

@composite
def reportEntries(draw: Callable) -> ReportEntry:
    created   = draw(datetimes())
    author    = draw(text(min_size=1))
    automatic = draw(booleans())
    entryText = draw(text(min_size=1))

    return ReportEntry(
        created=created, author=author, automatic=automatic, text=entryText
    )


##
# Event
##

@composite
def events(draw: Callable) -> Event:
    id = draw(text(min_size=1))

    return Event(id=id)


##
# Location
##

@composite
def locations(draw: Callable) -> Location:
    name    = draw(text())
    address = draw(addresses())

    return Location(name=name, address=address)


##
# Priority
##

@composite
def incidentPriorities(draw: Callable) -> IncidentPriority:
    return draw(sampledFrom(IncidentPriority))


##
# Report
##

@composite
def incidentReports(draw: Callable) -> IncidentReport:
    number  = draw(integers(min_value=1))
    created = draw(datetimes())
    summary = draw(text(min_size=1))

    entries = tuple(sorted(
        draw(reportEntries())
        for i in range(draw(integers(min_value=0, max_value=10)))
    ))

    return IncidentReport(
        number=number,
        created=created,
        summary=summary,
        reportEntries=entries,
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
def incidentTypes(draw: Callable) -> IncidentType:
    return draw(sampledFrom(IncidentType))
