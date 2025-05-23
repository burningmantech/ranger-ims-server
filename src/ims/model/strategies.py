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

from collections.abc import Callable, Hashable, Sequence
from datetime import UTC
from datetime import datetime as DateTime
from datetime import timedelta as TimeDelta
from datetime import timezone as TimeZone
from string import ascii_letters
from typing import Any, cast

from hypothesis.strategies import (
    SearchStrategy,
    booleans,
    characters,
    composite,
    dictionaries,
    emails,
    integers,
    lists,
    none,
    one_of,
    sampled_from,
    text,
)
from hypothesis.strategies import datetimes as _datetimes

from ims.directory import hashPassword
from ims.ext.sqlite import SQLITE_MAX_INT

from ._accessentry import AccessEntry
from ._accessvalidity import AccessValidity
from ._address import Address, RodGarettAddress, TextOnlyAddress
from ._entry import ReportEntry
from ._event import Event
from ._eventaccess import EventAccess
from ._eventdata import EventData
from ._imsdata import IMSData
from ._incident import Incident
from ._location import Location
from ._position import Position
from ._priority import IncidentPriority
from ._ranger import Ranger, RangerStatus
from ._report import FieldReport
from ._state import IncidentState
from ._team import Team
from ._type import IncidentType, KnownIncidentType


__all__ = (
    "addresses",
    "concentricStreetIDs",
    "concentricStreetNames",
    "dateTimes",
    "eventAccesses",
    "eventDatas",
    "events",
    "fieldReportLists",
    "fieldReportNumbers",
    "fieldReportSummaries",
    "fieldReports",
    "imsDatas",
    "incidentLists",
    "incidentNumbers",
    "incidentPriorities",
    "incidentStates",
    "incidentSummaries",
    "incidentTypes",
    "incidents",
    "locationNames",
    "locations",
    "positions",
    "radialHours",
    "radialMinutes",
    "rangerHandles",
    "rangers",
    "reportEntries",
    "rodGarettAddresses",
    "teams",
    "textOnlyAddresses",
    "timeZones",
)


##
# DateTimes
##


@composite
def timeZones(draw: Callable[..., Any]) -> TimeZone:
    """
    Strategy that generates :class:`TimeZone` values.
    """
    offset = draw(integers(min_value=-(60 * 24) + 1, max_value=(60 * 24) - 1))
    timeDelta = TimeDelta(minutes=offset)
    return TimeZone(offset=timeDelta, name=f"{offset}s")


def dateTimes(
    beforeNow: bool = False, fromNow: bool = False
) -> SearchStrategy[DateTime]:
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
        max = DateTime.now(tz=UTC) - fuzz
    else:
        max = DateTime(9999, 12, 31, 23, 59, 59, 999999)

    if fromNow:
        min = DateTime.now(tz=UTC) + fuzz
    else:
        min = DateTime(1970, 1, 1) + fuzz

    return _datetimes(min_value=min, max_value=max, timezones=timeZones())


##
# Address
##


@composite
def textOnlyAddresses(draw: Callable[..., Any]) -> TextOnlyAddress:
    """
    Strategy that generates :class:`TextOnlyAddress` values.
    """
    return TextOnlyAddress(description=draw(text()))


def concentricStreetIDs() -> SearchStrategy[str]:
    """
    Strategy that generates concentric street IDs.
    """
    return text()


def concentricStreetNames() -> SearchStrategy[str]:
    """
    Strategy that generates concentric street names.
    """
    return text()


def radialHours() -> SearchStrategy:  # int
    """
    Strategy that generates radial street hour values.
    """
    return integers(min_value=1, max_value=12)


def radialMinutes() -> SearchStrategy[str]:
    """
    Strategy that generates radial street minute values.
    """
    return integers(min_value=0, max_value=59)


@composite
def rodGarettAddresses(draw: Callable[..., Any]) -> RodGarettAddress:
    """
    Strategy that generates :class:`RodGarettAddress` values.
    """
    return RodGarettAddress(
        concentric=draw(concentricStreetIDs()),
        radialHour=draw(radialHours()),
        radialMinute=draw(radialMinutes()),
        description=draw(text()),
    )


def addresses() -> SearchStrategy[Address]:
    """
    Strategy that generates :class:`Address` values.
    """
    return one_of(none(), textOnlyAddresses(), rodGarettAddresses())


##
# Entry
##


@composite
def reportEntries(
    draw: Callable[..., Any],
    author: str | None = None,
    automatic: bool | None = None,
    beforeNow: bool = False,
    fromNow: bool = False,
    noAttachedFile: bool = False,
) -> ReportEntry:
    """
    Strategy that generates :class:`ReportEntry` values.
    """
    if author is None:
        author = draw(text(min_size=1))

    if automatic is None:
        automatic = draw(booleans())

    return ReportEntry(
        id=draw(integers(min_value=1, max_value=SQLITE_MAX_INT)),
        created=draw(dateTimes(beforeNow=beforeNow, fromNow=fromNow)),
        author=cast("str", author),
        automatic=cast("bool", automatic),
        text=draw(text(min_size=1)),
        stricken=False,
        attachedFile=None if noAttachedFile else draw(text()),
    )


##
# Event
##


@composite
def events(draw: Callable[..., Any]) -> Event:
    """
    Strategy that generates :class:`Event` values.
    """
    # The Event ID can consist of characters that match
    # \w_-

    allow_letters = [*list(ascii_letters), "-", "_"]
    return Event(
        id=draw(
            text(
                min_size=1,
                alphabet=characters(
                    # Include the digits 0-9 too
                    min_codepoint=0x30,
                    max_codepoint=0x39,
                    include_characters=allow_letters,
                ),
            )
        )
    )


@composite
def accessTexts(draw: Callable[..., Any]) -> str:
    """
    Strategy that generates event access strings.
    """
    # FIXME: We are using Ranger handles for positions here.
    return "{}:{}".format(
        draw(sampled_from(("person", "position"))),
        draw(rangerHandles()),
    )


@composite
def accessEntries(draw: Callable[..., Any]) -> AccessEntry:
    return AccessEntry(
        expression=draw(accessTexts()),
        validity=AccessValidity.always,
    )


@composite
def eventAccesses(draw: Callable[..., Any]) -> EventAccess:
    """
    Strategy that generates :class:`EventAccess` values.
    """
    readers: Sequence[AccessEntry] = tuple(draw(lists(accessEntries())))
    writers: Sequence[AccessEntry] = tuple(
        a for a in draw(lists(accessEntries())) if a not in readers
    )
    reporters: Sequence[AccessEntry] = tuple(
        a for a in draw(lists(accessEntries())) if a not in readers and a not in writers
    )
    return EventAccess(readers=readers, writers=writers, reporters=reporters)


@composite
def eventDatas(draw: Callable[..., Any]) -> EventData:
    """
    Strategy that generates :class:`EventData` values.
    """
    event: Event = draw(events())
    concentricStreets: dict[str, str] = draw(
        dictionaries(keys=concentricStreetIDs(), values=concentricStreetNames())
    )
    situations: list[Incident] = draw(
        lists(incidents(event=event), unique_by=lambda i: i.number)
    )

    # Add all concentric streets referred to by incidents so the data is valid
    for incident in situations:
        address = incident.location.address
        if (
            isinstance(address, RodGarettAddress)
            and address.concentric is not None
            and address.concentric not in concentricStreets
        ):
            concentricStreets[address.concentric] = draw(concentricStreetNames())

    return EventData(
        event=event,
        access=draw(eventAccesses()),
        concentricStreets=concentricStreets,
        incidents=situations,
        fieldReports=draw(
            lists(fieldReports(event=event), unique_by=lambda i: i.number)
        ),
    )


@composite
def imsDatas(draw: Callable[..., Any]) -> IMSData:
    """
    Strategy that generates :class:`IMSData` values.
    """
    events: list[EventData] = draw(lists(eventDatas(), unique_by=lambda d: d.event.id))

    types: dict[str, IncidentType] = {
        incidentType.name: incidentType
        for incidentType in draw(lists(incidentTypes(), unique_by=lambda t: t.name))
    }

    # Add all incident types referred to by incidents so the data is valid
    for eventData in events:
        for incident in eventData.incidents:
            for name in incident.incidentTypes:
                if name not in types:
                    types[name] = IncidentType(name=name, hidden=False)

    return IMSData(events=events, incidentTypes=types.values())


##
# Incident
##

maxIncidentNumber = min(
    (
        SQLITE_MAX_INT,
        4294967295,
    )
)  # SQLite  # MySQL


def incidentNumbers() -> SearchStrategy[str]:
    """
    Strategy that generates incident numbers.
    """
    return integers(min_value=1, max_value=maxIncidentNumber)


def incidentSummaries() -> SearchStrategy[str]:
    """
    Strategy that generates incident summaries.
    """
    return one_of(none(), text())


@composite
def incidents(
    draw: Callable[..., Any],
    new: bool = False,
    event: Event | None = None,
    beforeNow: bool = False,
    fromNow: bool = False,
) -> Incident:
    """
    Strategy that generates :class:`Incident` values.
    """
    automatic: bool | None
    if new:
        number = 0
        automatic = False
    else:
        number = draw(incidentNumbers())
        automatic = None

    if event is None:
        event = draw(events())

    types = [t.name for t in draw(lists(incidentTypes()))]

    created = draw(dateTimes(beforeNow=beforeNow, fromNow=fromNow))
    entries = draw(
        lists(reportEntries(automatic=automatic, beforeNow=beforeNow, fromNow=fromNow))
    )
    lastModified = max(re.created for re in entries) if entries else created
    return Incident(
        eventID=event.id,
        number=number,
        created=created,
        lastModified=lastModified,
        state=draw(incidentStates()),
        priority=draw(incidentPriorities()),
        summary=draw(incidentSummaries()),
        location=draw(locations()),
        rangerHandles=draw(lists(rangerHandles())),
        incidentTypes=types,
        reportEntries=entries,
        fieldReportNumbers=frozenset(),
    )


def incidentLists(
    event: Event | None = None,
    maxNumber: int | None = None,
    minSize: int | None = None,
    maxSize: int | None = None,
    averageSize: int | None = None,
    uniqueIDs: bool = False,
) -> SearchStrategy[list[Incident]]:
    """
    Strategy that generates :class:`List`s containing :class:`Incident` values.
    """
    uniqueBy: Callable[[Incident], Hashable] | None
    if uniqueIDs:

        def uniqueBy(incident: Incident) -> Hashable:
            return cast("Hashable", (incident.eventID, incident.number))

    else:
        uniqueBy = None

    return lists(
        incidents(event=event, maxNumber=maxNumber),
        min_size=minSize,
        max_size=maxSize,
        average_size=averageSize,
        unique_by=uniqueBy,
    )


##
# Location
##


def locationNames() -> SearchStrategy[str]:
    """
    Strategy that generates location names.
    """
    return text()


@composite
def locations(draw: Callable[..., Any]) -> Location:
    """
    Strategy that generates :class:`Location` values.
    """
    return Location(name=draw(locationNames()), address=draw(addresses()))


##
# Priority
##


def incidentPriorities() -> SearchStrategy[IncidentPriority]:
    """
    Strategy that generates :class:`IncidentPriority` values.
    """
    return sampled_from(IncidentPriority)


##
# Ranger
##


def rangerHandles() -> SearchStrategy[str]:
    """
    Strategy that generates Ranger handles.
    """
    return text(min_size=1)


@composite
def passwords(draw: Callable[..., Any]) -> str:
    """
    Strategy that generates hashed passwords.
    """
    password = draw(text())
    return hashPassword(password)


@composite
def rangers(draw: Callable[..., Any]) -> Ranger:
    """
    Strategy that generates :class:`Ranger` values.
    """
    return Ranger(
        handle=draw(rangerHandles()),
        status=draw(sampled_from(RangerStatus)),
        email=draw(lists(emails())),
        onsite=draw(booleans()),
        directoryID=draw(one_of(none(), text())),
        password=draw(one_of(none(), text())),
    )


##
# Position
##


@composite
def positions(draw: Callable[..., Any]) -> Position:
    """
    Strategy that generates :class:`Position` values.
    """
    return Position(
        name=draw(text(min_size=1)),
        members=frozenset(draw(lists(rangerHandles()))),
    )


##
# Team
##
@composite
def teams(draw: Callable[..., Any]) -> Team:
    """
    Strategy that generates :class:`Team` values.
    """
    return Team(
        name=draw(text(min_size=1)),
        members=frozenset(draw(lists(rangerHandles()))),
    )


##
# Report
##

fieldReportNumbers = incidentNumbers
fieldReportSummaries = incidentSummaries


@composite
def fieldReports(
    draw: Callable[..., Any],
    new: bool = False,
    event: Event | None = None,
    beforeNow: bool = False,
    fromNow: bool = False,
) -> FieldReport:
    """
    Strategy that generates :class:`FieldReport` values.
    """
    automatic: bool | None
    if new:
        number = 0
        automatic = False
    else:
        number = draw(fieldReportNumbers())
        automatic = None

    if event is None:
        event = draw(events())

    return FieldReport(
        eventID=event.id,
        number=number,
        created=draw(dateTimes(beforeNow=beforeNow, fromNow=fromNow)),
        summary=draw(fieldReportSummaries()),
        incidentNumber=None,  # FIXME: May allow some to be passed in?
        reportEntries=draw(
            lists(
                reportEntries(automatic=automatic, beforeNow=beforeNow, fromNow=fromNow)
            )
        ),
    )


def fieldReportLists(
    maxNumber: int | None = None,
    minSize: int | None = None,
    maxSize: int | None = None,
    averageSize: int | None = None,
) -> SearchStrategy[list[FieldReport]]:
    """
    Strategy that generates :class:`List`s containing :class:`FieldReport`
    values.
    """

    def uniqueBy(fieldReport: FieldReport) -> Hashable:
        return cast("Hashable", fieldReport.number)

    return lists(
        fieldReports(maxNumber=maxNumber),
        min_size=minSize,
        max_size=maxSize,
        average_size=averageSize,
        unique_by=uniqueBy,
    )


##
# State
##


def incidentStates() -> SearchStrategy[IncidentState]:
    """
    Strategy that generates :class:`IncidentState` values.
    """
    return sampled_from(IncidentState)


##
# Type
##


@composite
def incidentTypes(draw: Callable[..., Any]) -> IncidentType:
    """
    Strategy that generates incident types.
    """
    return IncidentType(
        name=draw(text(min_size=1)),
        hidden=draw(booleans()),
    )


def knownIncidentTypes() -> SearchStrategy[KnownIncidentType]:
    """
    Strategy that generates :class:`KnownIncidentType` values.
    """
    return sampled_from(KnownIncidentType)
