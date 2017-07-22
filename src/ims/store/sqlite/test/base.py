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

from pathlib import Path
from textwrap import dedent
from typing import Dict, Set, Union, cast

from attr import attrs

from ims.ext.sqlite import Connection, Cursor, SQLiteError
from ims.ext.trial import TestCase
from ims.model import Event, Incident, Location, RodGarettAddress

from .._store import DataStore, asTimeStamp, incidentStateAsID, priorityAsID

Dict, Set  # silence linter


__all__ = ()



@attrs(frozen=True)
class TestDataStore(DataStore):
    """
    :class:`DataStore` subclass that raises SQLiteError when things get
    interesting.
    """

    @property
    def _db(self) -> Connection:
        if getattr(self._state, "broken", False):
            raise SQLiteError("I'm broken, yo")

        return cast(property, DataStore._db).fget(self)


    def bringThePain(self) -> None:
        setattr(self._state, "broken", True)
        assert getattr(self._state, "broken")



class DataStoreTests(TestCase):
    """
    Tests for :class:`DataStore` base functionality.
    """

    def store(self) -> TestDataStore:
        return TestDataStore(dbPath=Path(self.mktemp()))


    # FIXME: A better plan here would be to create a mock DB object that yields
    # the expected rows, instead of writing to an actual DB.
    # Since it's SQLite, which isn't actually async, that's not a huge deal,
    # except there's a lot of fragile code below.

    def storeConcentricStreet(
        self, cursor: Union[Connection, Cursor], event: Event, streetID: str,
        streetName: str, ignoreDuplicates: bool = False,
    ) -> None:
        if ignoreDuplicates:
            ignore = " or ignore"
        else:
            ignore = ""

        cursor.execute(
            dedent(
                """
                insert{ignore} into CONCENTRIC_STREET (EVENT, ID, NAME)
                values (
                    (select ID from EVENT where NAME = :eventID),
                    :streetID,
                    :streetName
                )
                """.format(ignore=ignore)
            ),
            dict(
                eventID=event.id, streetID=streetID, streetName=streetName
            )
        )


    def normalizeAddress(self, incident: Incident) -> Incident:
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


    def storeIncident(self, store: DataStore, incident: Incident) -> None:
        with store._db as db:
            cursor = db.cursor()
            try:
                self._storeIncident(cursor, incident)
            finally:
                cursor.close()


    def _storeIncident(self, cursor: Cursor, incident: Incident) -> None:
        incident = self.normalizeAddress(incident)

        location = incident.location
        address = cast(RodGarettAddress, location.address)

        cursor.execute(
            "insert into EVENT (NAME) values (:eventID);",
            dict(eventID=incident.event.id)
        )

        if address.concentric is not None:
            self.storeConcentricStreet(
                cursor, incident.event, address.concentric, "Some Street"
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
                locationConcentric=address.concentric,
                locationRadialHour=address.radialHour,
                locationRadialMinute=address.radialMinute,
                locationDescription=address.description,
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
                    insert into INCIDENT_TYPE (NAME, HIDDEN)
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
