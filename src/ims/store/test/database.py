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
Tests for :mod:`ranger-ims-server.store` database stores
"""

from typing import ClassVar, cast

from attrs import frozen
from twisted.logger import Logger

from ims.model import (
    Event,
    FieldReport,
    Incident,
    Location,
    RodGarettAddress,
    TextOnlyAddress,
)

from .._db import DatabaseStore, Transaction
from .._exceptions import StorageError
from .base import TestDataStoreMixIn


__all__ = ()


@frozen(kw_only=True)
class TestDatabaseStoreMixIn(TestDataStoreMixIn):
    """
    MixIn for test data stores backed by databases.
    """

    _log: ClassVar[Logger] = Logger()

    async def storeEvent(self, event: Event) -> None:
        """
        Store the given event in the test store.
        """
        store = cast(DatabaseStore, self)

        try:
            await store.runOperation(store.query.createEvent, {"eventID": event.id})
        except StorageError as e:
            self._log.critical(
                "Unable to store event {event}: {error}", event=event, error=e
            )
            raise

        self._log.info("Stored event {event}.", event=event)

    def _storeIncident(self, txn: Transaction, incident: Incident) -> None:
        store = cast(DatabaseStore, self)

        incident = self.normalizeIncidentAddress(incident)

        location = incident.location
        address = cast(RodGarettAddress | None, location.address)

        txn.execute(
            store.query.createEventOrIgnore.text,
            {"eventID": incident.eventID},
        )

        if address is None:
            locationConcentric = None
            locationRadialHour = None
            locationRadialMinute = None
            locationDescription = None
        else:
            locationConcentric = address.concentric
            locationRadialHour = address.radialHour
            locationRadialMinute = address.radialMinute
            locationDescription = address.description

            if address.concentric is not None:
                self._storeConcentricStreet(
                    txn,
                    incident.eventID,
                    address.concentric,
                    "Some Street",
                    ignoreDuplicates=True,
                )

        txn.execute(
            store.query.createIncident.text,
            {
                "eventID": incident.eventID,
                "incidentCreated": store.asDateTimeValue(incident.created),
                "incidentNumber": incident.number,
                "incidentSummary": incident.summary,
                "incidentPriority": store.asPriorityValue(incident.priority),
                "incidentState": store.asIncidentStateValue(incident.state),
                "locationName": location.name,
                "locationConcentric": locationConcentric,
                "locationRadialHour": locationRadialHour,
                "locationRadialMinute": locationRadialMinute,
                "locationDescription": locationDescription,
            },
        )

        for rangerHandle in incident.rangerHandles:
            txn.execute(
                store.query.attachRangerHandleToIncident.text,
                {
                    "eventID": incident.eventID,
                    "incidentNumber": incident.number,
                    "rangerHandle": rangerHandle,
                },
            )

        for incidentType in incident.incidentTypes:
            txn.execute(
                store.query.createIncidentTypeOrIgnore.text,
                {"incidentType": incidentType},
            )
            txn.execute(
                store.query.attachIncidentTypeToIncident.text,
                {
                    "eventID": incident.eventID,
                    "incidentNumber": incident.number,
                    "incidentType": incidentType,
                },
            )

        for reportEntry in incident.reportEntries:
            txn.execute(
                store.query.createReportEntry.text,
                {
                    "created": store.asDateTimeValue(reportEntry.created),
                    "author": reportEntry.author,
                    "automatic": reportEntry.automatic,
                    "text": reportEntry.text,
                },
            )
            txn.execute(
                store.query.attachReportEntryToIncident.text,
                {
                    "eventID": incident.eventID,
                    "incidentNumber": incident.number,
                    "reportEntryID": txn.lastrowid,
                },
            )

    async def storeIncident(self, incident: Incident) -> None:
        """
        Store the given incident in the test store.
        """
        store = cast(DatabaseStore, self)

        try:
            await store.runInteraction(self._storeIncident, incident=incident)
        except StorageError as e:
            self._log.critical(
                "Unable to store incident {incident}: {error}",
                incident=incident,
                error=e,
            )
            raise

        self._log.info("Stored incident {incident}.", incident=incident)

    def _storeFieldReport(self, txn: Transaction, fieldReport: FieldReport) -> None:
        store = cast(DatabaseStore, self)

        txn.execute(
            store.query.createEventOrIgnore.text,
            {"eventID": fieldReport.eventID},
        )

        txn.execute(
            store.query.createFieldReport.text,
            {
                "eventID": fieldReport.eventID,
                "fieldReportNumber": fieldReport.number,
                "fieldReportCreated": store.asDateTimeValue(fieldReport.created),
                "fieldReportSummary": fieldReport.summary,
                "incidentNumber": fieldReport.incidentNumber,
            },
        )

        for reportEntry in fieldReport.reportEntries:
            txn.execute(
                store.query.createReportEntry.text,
                {
                    "created": store.asDateTimeValue(reportEntry.created),
                    "author": reportEntry.author,
                    "automatic": reportEntry.automatic,
                    "text": reportEntry.text,
                },
            )
            txn.execute(
                store.query.attachReportEntryToFieldReport.text,
                {
                    "fieldReportNumber": fieldReport.number,
                    "reportEntryID": txn.lastrowid,
                },
            )

    async def storeFieldReport(self, fieldReport: FieldReport) -> None:
        """
        Store the given field report in the test store.
        """
        store = cast(DatabaseStore, self)

        try:
            await store.runInteraction(self._storeFieldReport, fieldReport=fieldReport)
        except StorageError as e:
            self._log.critical(
                "Unable to store field report {fieldReport}: {error}",
                fieldReport=fieldReport,
                error=e,
            )
            raise

        self._log.info(
            "Stored field report {fieldReport}.",
            fieldReport=fieldReport,
        )

    def _storeConcentricStreet(
        self,
        txn: Transaction,
        eventID: str,
        streetID: str,
        streetName: str,
        ignoreDuplicates: bool = False,
    ) -> None:
        store = cast(DatabaseStore, self)

        if ignoreDuplicates:
            query = store.query.createConcentricStreetOrIgnore
        else:
            query = store.query.createConcentricStreet

        txn.execute(
            query.text,
            {"eventID": eventID, "streetID": streetID, "streetName": streetName},
        )

    async def storeConcentricStreet(
        self,
        eventID: str,
        streetID: str,
        streetName: str,
        ignoreDuplicates: bool = False,
    ) -> None:
        """
        Store a concentric street in the given event with the given ID and name
        in the test store.
        """
        store = cast(DatabaseStore, self)

        try:
            await store.runInteraction(
                self._storeConcentricStreet,
                eventID=eventID,
                streetID=streetID,
                streetName=streetName,
                ignoreDuplicates=ignoreDuplicates,
            )
        except StorageError as e:
            self._log.critical(
                "Unable to store concentric street {streetName} "
                "({streetID}, ignore={ignoreDuplicates}) in event {eventID}: "
                "{error}",
                eventID=eventID,
                streetID=streetID,
                streetName=streetName,
                ignoreDuplicates=ignoreDuplicates,
                error=e,
            )
            raise

        self._log.info(
            "Stored concentric street {streetName} "
            "({streetID}, ignore={ignoreDuplicates}) in event {eventID}.",
            eventID=eventID,
            streetID=streetID,
            streetName=streetName,
            ignoreDuplicates=ignoreDuplicates,
        )

    def _storeIncidentType(
        self, txn: Transaction, incidentType: str, hidden: bool
    ) -> None:
        store = cast(DatabaseStore, self)

        txn.execute(
            store.query.createIncidentType.text,
            {"incidentType": incidentType, "hidden": hidden},
        )

    async def storeIncidentType(self, incidentType: str, hidden: bool) -> None:
        store = cast(DatabaseStore, self)

        try:
            await store.runInteraction(
                self._storeIncidentType,
                incidentType=incidentType,
                hidden=hidden,
            )
        except StorageError as e:
            self._log.critical(
                "Unable to store incident type {incidentType} "
                "(hidden={hidden}): {error}",
                incidentType=incidentType,
                hidden=hidden,
                error=e,
            )
            raise

        self._log.info(
            "Stored incident type {incidentType} (hidden={hidden}).",
            incidentType=incidentType,
            hidden=hidden,
        )

    @staticmethod
    def normalizeIncidentAddress(incident: Incident) -> Incident:
        # Normalize address to Rod Garett; DB schema only supports those.
        address = incident.location.address
        if isinstance(address, TextOnlyAddress):
            incident = incident.replace(
                location=Location(
                    name=incident.location.name,
                    address=RodGarettAddress(
                        description=address.description,
                    ),
                )
            )
        else:
            assert isinstance(address, RodGarettAddress)
        return incident
