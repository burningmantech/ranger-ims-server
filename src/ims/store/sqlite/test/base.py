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
Tests for :mod:`ranger-ims-server.store.sqlite._store`
"""

from datetime import datetime as DateTime, timedelta as TimeDelta
from pathlib import Path
from textwrap import dedent
from typing import Optional, Sequence, Union, cast

from ims.ext.sqlite import Connection, Cursor, SQLITE_MAX_INT, SQLiteError
from ims.ext.trial import TestCase
from ims.model import (
    Event, Incident, IncidentReport, Location, ReportEntry, RodGarettAddress
)

from .._store import DataStore, asTimeStamp, incidentStateAsID, priorityAsID
from ...test.base import TestDataStore as SuperTestDataStore


__all__ = ()



class TestDataStore(SuperTestDataStore, DataStore):
    """
    See :class:`SuperTestDataStore`.
    """

    maxIncidentNumber = SQLITE_MAX_INT

    exceptionClass = SQLiteError


    def __init__(
        self, testCase: TestCase, dbPath: Optional[Path] = None
    ) -> None:
        if dbPath is None:
            dbPath = Path(testCase.mktemp())
        DataStore.__init__(self, dbPath)


    @property
    def _db(self) -> Connection:
        if getattr(self._state, "broken", False):
            self.raiseException()

        return cast(property, DataStore._db).fget(self)


    def bringThePain(self) -> None:
        setattr(self._state, "broken", True)
        assert getattr(self._state, "broken")


    def storeEvent(self, event: Event) -> None:
        with self._db as db:
            cursor: Cursor = db.cursor()
            try:
                storeEvent(cursor, event)
            finally:
                cursor.close()


    def storeIncident(self, incident: Incident) -> None:
        with self._db as db:
            cursor: Cursor = db.cursor()
            try:
                storeIncident(cursor, incident)
            finally:
                cursor.close()


    def storeIncidentReport(
        self, incidentReport: IncidentReport
    ) -> None:
        with self._db as db:
            cursor: Cursor = db.cursor()
            try:
                storeIncidentReport(cursor, incidentReport)
            finally:
                cursor.close()


    def storeConcentricStreet(
        self, event: Event, streetID: str, streetName: str,
        ignoreDuplicates: bool = False,
    ) -> None:
        with self._db as db:
            cursor: Cursor = db.cursor()
            try:
                storeConcentricStreet(
                    cursor, event, streetID, streetName, ignoreDuplicates
                )
            finally:
                cursor.close()


    def storeIncidentType(self, name: str, hidden: bool) -> None:
        with self._db as db:
            cursor: Cursor = db.cursor()
            try:
                storeIncidentType(cursor, name, hidden)
            finally:
                cursor.close()


    def dateTimesEqual(self, a: DateTime, b: DateTime) -> bool:
        # Floats stored in SQLite may be slightly off when round-tripped.
        return a - b < TimeDelta(microseconds=20)


    def reportEntriesEqual(
        self,
        reportEntriesA: Sequence[ReportEntry],
        reportEntriesB: Sequence[ReportEntry],
        ignoreAutomatic: bool = False,
    ) -> bool:
        if ignoreAutomatic:
            reportEntriesA = tuple(
                e for e in reportEntriesA if not e.automatic
            )

        if len(reportEntriesA) != len(reportEntriesB):
            return False

        for entryA, entryB in zip(reportEntriesA, reportEntriesB):
            if entryA != entryB:
                if entryA.author != entryB.author:
                    return False
                if entryA.automatic != entryB.automatic:
                    return False
                if entryA.text != entryB.text:
                    return False
                if not self.dateTimesEqual(
                    entryA.created, entryB.created
                ):
                    return False

        return True


    @staticmethod
    def normalizeIncidentAddress(incident: Incident) -> Incident:
        # Normalize address to Rod Garett; DB schema only supports those.
        address = incident.location.address
        if address is not None and not isinstance(address, RodGarettAddress):
            incident = incident.replace(
                location=Location(
                    name=incident.location.name,
                    address=RodGarettAddress(
                        description=address.description,
                    )
                )
            )
        return incident



def storeEvent(cursor: Cursor, event: Event) -> None:
    cursor.execute(
        "insert into EVENT (NAME) values (:eventID)",
        dict(eventID=event.id)
    )


def storeIncident(cursor: Cursor, incident: Incident) -> None:
    incident = TestDataStore.normalizeIncidentAddress(incident)

    location = incident.location
    address = cast(RodGarettAddress, location.address)

    cursor.execute(
        "insert or ignore into EVENT (NAME) values (:eventID);",
        dict(eventID=incident.event.id)
    )

    if address is None:
        locationConcentric   = None
        locationRadialHour   = None
        locationRadialMinute = None
        locationDescription  = None
    else:
        locationConcentric   = address.concentric
        locationRadialHour   = address.radialHour
        locationRadialMinute = address.radialMinute
        locationDescription  = address.description

        if address.concentric is not None:
            storeConcentricStreet(
                cursor, incident.event, address.concentric, "Some Street",
                ignoreDuplicates=True,
            )

    cursor.execute(
        dedent(
            """
            insert into INCIDENT (
                EVENT, NUMBER, VERSION, CREATED, PRIORITY, STATE, SUMMARY,
                LOCATION_NAME,
                LOCATION_CONCENTRIC,
                LOCATION_RADIAL_HOUR,
                LOCATION_RADIAL_MINUTE,
                LOCATION_DESCRIPTION
            ) values (
                (select ID from EVENT where NAME = :eventID),
                :incidentNumber,
                1,
                :incidentCreated,
                :incidentPriority,
                :incidentState,
                :incidentSummary,
                :locationName,
                :locationConcentric,
                :locationRadialHour,
                :locationRadialMinute,
                :locationDescription
            )
            """
        ),
        dict(
            eventID=incident.event.id,
            incidentCreated=asTimeStamp(incident.created),
            incidentNumber=incident.number,
            incidentSummary=incident.summary,
            incidentPriority=priorityAsID(incident.priority),
            incidentState=incidentStateAsID(incident.state),
            locationName=location.name,
            locationConcentric=locationConcentric,
            locationRadialHour=locationRadialHour,
            locationRadialMinute=locationRadialMinute,
            locationDescription=locationDescription,
        )
    )

    for rangerHandle in incident.rangerHandles:
        cursor.execute(
            dedent(
                """
                insert into INCIDENT__RANGER
                (EVENT, INCIDENT_NUMBER, RANGER_HANDLE)
                values (
                    (select ID from EVENT where NAME = :eventID),
                    :incidentNumber,
                    :rangerHandle
                )
                """
            ),
            dict(
                eventID=incident.event.id,
                incidentNumber=incident.number,
                rangerHandle=rangerHandle
            )
        )

    for incidentType in incident.incidentTypes:
        cursor.execute(
            dedent(
                """
                insert or ignore into INCIDENT_TYPE (NAME, HIDDEN)
                values (:incidentType, 0)
                """
            ),
            dict(incidentType=incidentType)
        )
        cursor.execute(
            dedent(
                """
                insert into INCIDENT__INCIDENT_TYPE
                (EVENT, INCIDENT_NUMBER, INCIDENT_TYPE)
                values (
                    (select ID from EVENT where NAME = :eventID),
                    :incidentNumber,
                    (
                        select ID from INCIDENT_TYPE
                        where NAME = :incidentType
                    )
                )
                """
            ),
            dict(
                eventID=incident.event.id,
                incidentNumber=incident.number,
                incidentType=incidentType
            )
        )

    for reportEntry in incident.reportEntries:
        cursor.execute(
            dedent(
                """
                insert into REPORT_ENTRY (AUTHOR, TEXT, CREATED, GENERATED)
                values (:author, :text, :created, :automatic)
                """
            ),
            dict(
                created=asTimeStamp(reportEntry.created),
                author=reportEntry.author,
                automatic=reportEntry.automatic,
                text=reportEntry.text,
            )
        )
        cursor.execute(
            dedent(
                """
                insert into INCIDENT__REPORT_ENTRY (
                    EVENT, INCIDENT_NUMBER, REPORT_ENTRY
                )
                values (
                    (select ID from EVENT where NAME = :eventID),
                    :incidentNumber,
                    :reportEntryID
                )
                """
            ),
            dict(
                eventID=incident.event.id,
                incidentNumber=incident.number,
                reportEntryID=cursor.lastrowid
            )
        )


def storeConcentricStreet(
    cursor: Union[Connection, Cursor], event: Event, streetID: str,
    streetName: str, ignoreDuplicates: bool = False,
) -> None:
    if ignoreDuplicates:
        ignore = " or ignore"
    else:
        ignore = ""

    cursor.execute(
        dedent(
            f"""
            insert{ignore} into CONCENTRIC_STREET (EVENT, ID, NAME)
            values (
                (select ID from EVENT where NAME = :eventID),
                :streetID,
                :streetName
            )
            """
        ),
        dict(
            eventID=event.id, streetID=streetID, streetName=streetName
        )
    )


def storeIncidentReport(
    cursor: Cursor, incidentReport: IncidentReport
) -> None:
    cursor.execute(
        dedent(
            """
            insert into INCIDENT_REPORT (NUMBER, CREATED, SUMMARY)
            values (
                :incidentReportNumber,
                :incidentReportCreated,
                :incidentReportSummary
            )
            """
        ),
        dict(
            incidentReportCreated=asTimeStamp(incidentReport.created),
            incidentReportNumber=incidentReport.number,
            incidentReportSummary=incidentReport.summary,
        )
    )

    for reportEntry in incidentReport.reportEntries:
        cursor.execute(
            dedent(
                """
                insert into REPORT_ENTRY (AUTHOR, TEXT, CREATED, GENERATED)
                values (:author, :text, :created, :automatic)
                """
            ),
            dict(
                created=asTimeStamp(reportEntry.created),
                author=reportEntry.author,
                automatic=reportEntry.automatic,
                text=reportEntry.text,
            )
        )
        cursor.execute(
            dedent(
                """
                insert into INCIDENT_REPORT__REPORT_ENTRY (
                    INCIDENT_REPORT_NUMBER, REPORT_ENTRY
                )
                values (:incidentReportNumber, :reportEntryID)
                """
            ),
            dict(
                incidentReportNumber=incidentReport.number,
                reportEntryID=cursor.lastrowid
            )
        )


def storeIncidentType(cursor: Cursor, name: str, hidden: bool) -> None:
    cursor.execute(
        "insert into INCIDENT_TYPE (NAME, HIDDEN) "
        "values (:name, :hidden)",
        dict(name=name, hidden=hidden)
    )
