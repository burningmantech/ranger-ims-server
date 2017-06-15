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

from datetime import (
    datetime as DateTime, timedelta as TimeDelta, timezone as TimeZone
)
from typing import Callable, Optional

from hypothesis.strategies import (
    booleans, composite, datetimes as _datetimes, integers, iterables, none,
    one_of, sampled_from, text,
)

from ._address import Address, RodGarettAddress, TextOnlyAddress
from ._entry import ReportEntry
from ._event import Event
from ._incident import Incident
from ._location import Location
from ._priority import IncidentPriority
from ._ranger import Ranger, RangerStatus
from ._report import IncidentReport
from ._state import IncidentState
from ._type import KnownIncidentType


__all__ = (
    "addresses",
    "concentricStreetIDs",
    "concentricStreetNames",
    "dateTimes",
    "events",
    "incidentNumbers",
    "incidentPriorities",
    "incidentReportNumbers",
    "incidentReports",
    "incidentStates",
    "incidentSummaries",
    "incidentTypes",
    "incidentTypesText",
    "incidents",
    "locations",
    "radialHours",
    "radialMinutes",
    "rangerHandles",
    "rangers",
    "reportEntries",
    "rodGarettAddresses",
    "textOnlyAddresses",
)


##
# DateTimes
##


@composite
def timeZones(draw: Callable) -> TimeZone:
    offset = draw(integers(min_value=-(60 * 24) + 1, max_value=(60 * 24) - 1))
    timeDelta = TimeDelta(minutes=offset)
    timeZone = TimeZone(offset=timeDelta, name="{}s".format(offset))
    return timeZone


@composite
def dateTimes(draw: Callable) -> DateTime:
    return draw(_datetimes(
        min_datetime=DateTime(1970, 1, 1),  # Post- UTC epoch
        timezones=timeZones(),
    ))


##
# Address
##

@composite
def textOnlyAddresses(draw: Callable) -> TextOnlyAddress:
    return TextOnlyAddress(description=draw(text()))


@composite
def concentricStreetIDs(draw: Callable) -> str:
    return draw(text())


@composite
def concentricStreetNames(draw: Callable) -> str:
    return draw(text())


@composite
def radialHours(draw: Callable) -> str:
    return draw(integers(min_value=1, max_value=12))


@composite
def radialMinutes(draw: Callable) -> str:
    return draw(integers(min_value=0, max_value=59))


@composite
def rodGarettAddresses(draw: Callable) -> RodGarettAddress:
    return RodGarettAddress(
        concentric=draw(concentricStreetIDs()),
        radialHour=draw(radialHours()),
        radialMinute=draw(radialMinutes()),
        description=draw(text()),
    )


@composite
def addresses(draw: Callable) -> Address:
    return draw(one_of((textOnlyAddresses(), rodGarettAddresses())))


##
# Entry
##

@composite
def reportEntries(
    draw: Callable, automatic: Optional[bool] = None
) -> ReportEntry:
    if automatic is None:
        automatic = draw(booleans())

    return ReportEntry(
        created=draw(dateTimes()),
        author=draw(text(min_size=1)),
        automatic=automatic,
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
def incidentNumbers(draw: Callable) -> str:
    return draw(integers(min_value=1))


@composite
def incidentSummaries(draw: Callable) -> str:
    return draw(one_of(none(), text()))


@composite
def incidents(draw: Callable, new: bool = False) -> Incident:
    automatic: Optional[bool]
    if new:
        number = 0
        automatic = False
    else:
        number = draw(incidentNumbers())
        automatic = None

    return Incident(
        event=draw(events()),
        number=number,
        created=draw(dateTimes()),
        state=draw(incidentStates()),
        priority=draw(incidentPriorities()),
        summary=draw(incidentSummaries()),
        location=draw(locations()),
        rangerHandles=draw(iterables(rangerHandles())),
        incidentTypes=draw(iterables(incidentTypesText())),
        reportEntries=draw(iterables(reportEntries(automatic=automatic))),
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
    return draw(sampled_from(IncidentPriority))


##
# Ranger
##

@composite
def rangerHandles(draw: Callable) -> str:
    return draw(text(min_size=1))


@composite
def rangers(draw: Callable) -> Ranger:
    return Ranger(
        handle=draw(rangerHandles()),
        name=draw(text(min_size=1)),
        status=draw(sampled_from(RangerStatus)),
        email=draw(iterables(text(min_size=1))),
        onSite=draw(booleans()),
        dmsID=draw(one_of(none(), integers())),
        password=draw(one_of(none(), text())),
    )


##
# Report
##

@composite
def incidentReportNumbers(draw: Callable) -> str:
    return draw(integers(min_value=0))


@composite
def incidentReports(draw: Callable) -> IncidentReport:
    return IncidentReport(
        number=draw(incidentReportNumbers()),
        created=draw(dateTimes()),
        summary=draw(text(min_size=1)),
        reportEntries=sorted(draw(iterables(reportEntries()))),
    )


##
# State
##

@composite
def incidentStates(draw: Callable) -> IncidentState:
    return draw(sampled_from(IncidentState))


##
# Type
##

@composite
def incidentTypesText(draw: Callable) -> str:
    return draw(text(min_size=1))


@composite
def incidentTypes(draw: Callable) -> KnownIncidentType:
    return draw(sampled_from(KnownIncidentType))
