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
from typing import Callable, Hashable, Optional, cast

from hypothesis import HealthCheck, settings
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.strategies import (
    booleans, composite, datetimes as _datetimes, integers, lists, none,
    one_of, sampled_from, text,
)

from ims.dms import hashPassword

from ._address import RodGarettAddress, TextOnlyAddress
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
    "incidentLists",
    "incidentNumbers",
    "incidentPriorities",
    "incidentReportLists",
    "incidentReportNumbers",
    "incidentReportSummaries",
    "incidentReports",
    "incidentStates",
    "incidentSummaries",
    "incidentTypes",
    "incidentTypesText",
    "incidents",
    "locationNames",
    "locations",
    "radialHours",
    "radialMinutes",
    "rangerHandles",
    "rangers",
    "reportEntries",
    "rodGarettAddresses",
    "textOnlyAddresses",
    "timeZones",
)


settings.register_profile(
    "ci", settings(
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
)
settings.load_profile("ci")


##
# DateTimes
##


@composite
def timeZones(draw: Callable) -> TimeZone:
    """
    Strategy that generates :class:`TimeZone` values.
    """
    offset = draw(integers(min_value=-(60 * 24) + 1, max_value=(60 * 24) - 1))
    timeDelta = TimeDelta(minutes=offset)
    timeZone = TimeZone(offset=timeDelta, name=f"{offset}s")
    return timeZone


def dateTimes(
    beforeNow: bool = False, fromNow: bool = False
) -> SearchStrategy:  # DateTime
    """
    Strategy that generates :class:`DateTime` values.
    """
    assert not (beforeNow and fromNow)

    #
    # min_value >= UTC epoch because otherwise we can't store dates as UTC
    # timestamps.
    #
    # We actually add a day of fuzz below because min_value doesn't allow
    # non-naive values (?!) so that ensures we have a value after the epoch
    #
    # For all current uses of model date-times in model objects in this module,
    # limiting values to those past the is totally OK.
    #
    fuzz = TimeDelta(days=1)

    if beforeNow:
        max = DateTime.now() - fuzz
    else:
        max = DateTime(9999, 12, 31, 23, 59, 59, 999999)

    if fromNow:
        min = DateTime.now() + fuzz
    else:
        min = DateTime(1970, 1, 1) + fuzz

    return _datetimes(
        min_value=min, max_value=max, timezones=timeZones()
    )


##
# Address
##

@composite
def textOnlyAddresses(draw: Callable) -> SearchStrategy:  # TextOnlyAddress
    """
    Strategy that generates :class:`TextOnlyAddress` values.
    """
    return TextOnlyAddress(description=draw(text()))


def concentricStreetIDs() -> SearchStrategy:  # str
    """
    Strategy that generates concentric street IDs.
    """
    return text()


def concentricStreetNames() -> SearchStrategy:  # str
    """
    Strategy that generates concentric street names.
    """
    return text()


def radialHours() -> SearchStrategy:  # int
    """
    Strategy that generates radial street hour values.
    """
    return integers(min_value=1, max_value=12)


def radialMinutes() -> SearchStrategy:  # str
    """
    Strategy that generates radial street minute values.
    """
    return integers(min_value=0, max_value=59)


@composite
def rodGarettAddresses(draw: Callable) -> RodGarettAddress:
    """
    Strategy that generates :class:`RodGarettAddress` values.
    """
    return RodGarettAddress(
        concentric=draw(concentricStreetIDs()),
        radialHour=draw(radialHours()),
        radialMinute=draw(radialMinutes()),
        description=draw(text()),
    )


def addresses() -> SearchStrategy:  # Address
    """
    Strategy that generates :class:`Address` values.
    """
    return one_of(none(), textOnlyAddresses(), rodGarettAddresses())


##
# Entry
##

@composite
def reportEntries(
    draw: Callable,
    author: Optional[str] = None,
    automatic: Optional[bool] = None,
    beforeNow: bool = False, fromNow: bool = False,
) -> ReportEntry:
    """
    Strategy that generates :class:`ReportEntry` values.
    """
    if author is None:
        author = draw(text(min_size=1))

    if automatic is None:
        automatic = draw(booleans())

    return ReportEntry(
        created=draw(dateTimes(beforeNow=beforeNow, fromNow=fromNow)),
        author=cast(str, author),
        automatic=cast(bool, automatic),
        text=draw(text(min_size=1)),
    )


##
# Event
##

@composite
def events(draw: Callable) -> Event:
    """
    Strategy that generates :class:`Event` values.
    """
    return Event(id=draw(text(min_size=1)))


##
# Incident
##

def incidentNumbers(max: Optional[int] = None) -> SearchStrategy:  # str
    """
    Strategy that generates incident numbers.
    """
    return integers(min_value=1, max_value=max)


def incidentSummaries() -> SearchStrategy:  # str
    """
    Strategy that generates incident summaries.
    """
    return one_of(none(), text())


@composite
def incidents(
    draw: Callable,
    new: bool = False,
    event: Optional[Event] = None,
    maxNumber: Optional[int] = None,
    beforeNow: bool = False, fromNow: bool = False,
) -> Incident:
    """
    Strategy that generates :class:`Incident` values.
    """
    automatic: Optional[bool]
    if new:
        number = 0
        automatic = False
    else:
        number = draw(incidentNumbers(max=maxNumber))
        automatic = None

    if event is None:
        event = draw(events())

    return Incident(
        event=cast(Event, event),
        number=number,
        created=draw(dateTimes(beforeNow=beforeNow, fromNow=fromNow)),
        state=draw(incidentStates()),
        priority=draw(incidentPriorities()),
        summary=draw(incidentSummaries()),
        location=draw(locations()),
        rangerHandles=draw(lists(rangerHandles())),
        incidentTypes=draw(lists(incidentTypesText())),
        reportEntries=draw(lists(reportEntries(
            automatic=automatic, beforeNow=beforeNow, fromNow=fromNow
        ))),
        incidentReportNumbers=frozenset(),
    )


def incidentLists(
    event: Optional[Event] = None,
    maxNumber: Optional[int] = None,
    minSize: Optional[int] = None,
    maxSize: Optional[int] = None,
    averageSize: Optional[int] = None,
    uniqueIDs: bool = False,
) -> SearchStrategy:  # List[Incident]
    """
    Strategy that generates :class:`List`s containing :class:`Incident` values.
    """
    uniqueBy: Optional[Callable[[Incident], Hashable]]
    if uniqueIDs:
        def uniqueBy(incident: Incident) -> Hashable:
            return cast(Hashable, (incident.event, incident.number))
    else:
        uniqueBy = None

    return lists(
        incidents(event=event, maxNumber=maxNumber),
        min_size=minSize, max_size=maxSize, average_size=averageSize,
        unique_by=uniqueBy
    )


##
# Location
##

def locationNames() -> SearchStrategy:  # str
    """
    Strategy that generates location names.
    """
    return text()


@composite
def locations(draw: Callable) -> Location:
    """
    Strategy that generates :class:`Location` values.
    """
    return Location(name=draw(locationNames()), address=draw(addresses()))


##
# Priority
##

def incidentPriorities() -> SearchStrategy:  # IncidentPriority
    """
    Strategy that generates :class:`IncidentPriority` values.
    """
    return sampled_from(IncidentPriority)


##
# Ranger
##

def rangerHandles() -> SearchStrategy:  # str
    """
    Strategy that generates Ranger handles.
    """
    return text(min_size=1)


@composite
def passwords(draw: Callable) -> str:
    """
    Strategy that generates hashed passwords.
    """
    password = draw(text())
    return hashPassword(password)


@composite
def rangers(draw: Callable) -> Ranger:
    """
    Strategy that generates :class:`Ranger` values.
    """
    return Ranger(
        handle=draw(rangerHandles()),
        name=draw(text(min_size=1)),
        status=draw(sampled_from(RangerStatus)),
        email=draw(lists(text(min_size=1))),
        onSite=draw(booleans()),
        dmsID=draw(one_of(none(), integers())),
        password=draw(one_of(none(), text())),
    )


##
# Report
##

incidentReportNumbers = incidentNumbers
incidentReportSummaries = incidentSummaries


@composite
def incidentReports(
    draw: Callable,
    new: bool = False,
    event: Optional[Event] = None,
    maxNumber: Optional[int] = None,
    beforeNow: bool = False, fromNow: bool = False,
) -> IncidentReport:
    """
    Strategy that generates :class:`IncidentReport` values.
    """
    automatic: Optional[bool]
    if new:
        number = 0
        automatic = False
    else:
        number = draw(incidentNumbers(max=maxNumber))
        automatic = None

    if event is None:
        event = draw(events())

    return IncidentReport(
        event=event,
        number=number,
        created=draw(dateTimes(beforeNow=beforeNow, fromNow=fromNow)),
        summary=draw(incidentReportSummaries()),
        incidentNumber=None,  # FIXME: May allow some to be passed in?
        reportEntries=draw(lists(reportEntries(
            automatic=automatic, beforeNow=beforeNow, fromNow=fromNow
        ))),
    )


def incidentReportLists(
    maxNumber: Optional[int] = None,
    minSize: Optional[int] = None,
    maxSize: Optional[int] = None,
    averageSize: Optional[int] = None,
) -> SearchStrategy:  # List[IncidentReport]
    """
    Strategy that generates :class:`List`s containing :class:`IncidentReport`
    values.
    """
    def uniqueBy(incidentReport: IncidentReport) -> Hashable:
        return cast(Hashable, incidentReport.number)

    return lists(
        incidentReports(maxNumber=maxNumber),
        min_size=minSize, max_size=maxSize, average_size=averageSize,
        unique_by=uniqueBy
    )


##
# State
##

def incidentStates() -> SearchStrategy:  # IncidentState
    """
    Strategy that generates :class:`IncidentState` values.
    """
    return sampled_from(IncidentState)


##
# Type
##

def incidentTypesText() -> SearchStrategy:  # str
    """
    Strategy that generates incident types.
    """
    return text(min_size=1)


def incidentTypes() -> SearchStrategy:  # KnownIncidentType
    """
    Strategy that generates :class:`KnownIncidentType` values.
    """
    return sampled_from(KnownIncidentType)
