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

from typing import cast

from ims.model import (
    Event, Incident, IncidentReport, Location, RodGarettAddress
)

from .base import TestDataStoreMixIn
from .._db import DatabaseStore, Transaction
from .._exceptions import StorageError


__all__ = ()



class TestDatabaseStoreMixIn(TestDataStoreMixIn):
    """
    MixIn for test data stores backed by databases.
    """

    async def storeEvent(_self, event: Event) -> None:
        """
        Store the given event in the test store.
        """
        self = cast(DatabaseStore, _self)

        try:
            await self.runOperation(
                self.query.createEvent, dict(eventID=event.id)
            )
        except StorageError as e:
            self._log.critical(
                "Unable to store event {event}: {error}", event=event, error=e
            )
            raise

        self._log.info(
            "Stored event {event}.", event=event
        )


    def _storeIncident(_self, txn: Transaction, incident: Incident) -> None:
        self = cast(DatabaseStore, _self)

        incident = _self.normalizeIncidentAddress(incident)

        location = incident.location
        address = cast(RodGarettAddress, location.address)

        txn.execute(
            self.query.createEventOrIgnore.text,
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
                _self._storeConcentricStreet(
                    txn, incident.event, address.concentric, "Some Street",
                    ignoreDuplicates=True,
                )

        txn.execute(
            self.query.createIncident.text,
            dict(
                eventID=incident.event.id,
                incidentCreated=self.asDateTimeValue(incident.created),
                incidentNumber=incident.number,
                incidentSummary=incident.summary,
                incidentPriority=self.asPriorityValue(incident.priority),
                incidentState=self.asIncidentStateValue(incident.state),
                locationName=location.name,
                locationConcentric=locationConcentric,
                locationRadialHour=locationRadialHour,
                locationRadialMinute=locationRadialMinute,
                locationDescription=locationDescription,
            )
        )

        for rangerHandle in incident.rangerHandles:
            txn.execute(
                self.query.attachRangeHandleToIncident.text,
                dict(
                    eventID=incident.event.id,
                    incidentNumber=incident.number,
                    rangerHandle=rangerHandle
                )
            )

        for incidentType in incident.incidentTypes:
            txn.execute(
                self.query.createIncidentTypeOrIgnore.text,
                dict(incidentType=incidentType)
            )
            txn.execute(
                self.query.attachIncidentTypeToIncident.text,
                dict(
                    eventID=incident.event.id,
                    incidentNumber=incident.number,
                    incidentType=incidentType
                )
            )

        for reportEntry in incident.reportEntries:
            txn.execute(
                self.query.createReportEntry.text,
                dict(
                    created=self.asDateTimeValue(reportEntry.created),
                    author=reportEntry.author,
                    automatic=reportEntry.automatic,
                    text=reportEntry.text,
                )
            )
            txn.execute(
                self.query.attachReportEntryToIncident.text,
                dict(
                    eventID=incident.event.id,
                    incidentNumber=incident.number,
                    reportEntryID=txn.lastrowid
                )
            )


    async def storeIncident(_self, incident: Incident) -> None:
        """
        Store the given incident in the test store.
        """
        self = cast(DatabaseStore, _self)

        try:
            await self.runInteraction(_self._storeIncident, incident=incident)
        except StorageError as e:
            self._log.critical(
                "Unable to store incident {incident}: {error}",
                incident=incident, error=e,
            )
            raise

        self._log.info(
            "Stored incident {incident}.", incident=incident
        )


    def _storeIncidentReport(
        _self, txn: Transaction, incidentReport: IncidentReport
    ) -> None:
        self = cast(DatabaseStore, _self)

        txn.execute(
            self.query.createEventOrIgnore.text,
            dict(eventID=incidentReport.event.id)
        )

        txn.execute(
            self.query.createIncidentReport.text,
            dict(
                eventID=incidentReport.event.id,
                incidentReportNumber=incidentReport.number,
                incidentReportCreated=self.asDateTimeValue(
                    incidentReport.created
                ),
                incidentReportSummary=incidentReport.summary,
                incidentNumber=incidentReport.incidentNumber,
            )
        )

        for reportEntry in incidentReport.reportEntries:
            txn.execute(
                self.query.createReportEntry.text,
                dict(
                    created=self.asDateTimeValue(reportEntry.created),
                    author=reportEntry.author,
                    automatic=reportEntry.automatic,
                    text=reportEntry.text,
                )
            )
            txn.execute(
                self.query.attachReportEntryToIncidentReport.text,
                dict(
                    incidentReportNumber=incidentReport.number,
                    reportEntryID=txn.lastrowid
                )
            )


    async def storeIncidentReport(
        _self, incidentReport: IncidentReport
    ) -> None:
        """
        Store the given incident report in the test store.
        """
        self = cast(DatabaseStore, _self)

        try:
            await self.runInteraction(
                _self._storeIncidentReport, incidentReport=incidentReport
            )
        except StorageError as e:
            self._log.critical(
                "Unable to store incident report {incidentReport}: {error}",
                incidentReport=incidentReport, error=e,
            )
            raise

        self._log.info(
            "Stored incident report {incidentReport}.",
            incidentReport=incidentReport,
        )


    def _storeConcentricStreet(
        _self, txn: Transaction, event: Event, streetID: str, streetName: str,
        ignoreDuplicates: bool = False,
    ) -> None:
        self = cast(DatabaseStore, _self)

        if ignoreDuplicates:
            query = self.query.createConcentricStreetOrIgnore
        else:
            query = self.query.createConcentricStreet

        txn.execute(
            query.text,
            dict(
                eventID=event.id, streetID=streetID, streetName=streetName
            )
        )


    async def storeConcentricStreet(
        _self, event: Event, streetID: str, streetName: str,
        ignoreDuplicates: bool = False,
    ) -> None:
        """
        Store a concentric street in the given event with the given ID and name
        in the test store.
        """
        self = cast(DatabaseStore, _self)

        try:
            await self.runInteraction(
                _self._storeConcentricStreet,
                event=event, streetID=streetID, streetName=streetName,
                ignoreDuplicates=ignoreDuplicates,
            )
        except StorageError as e:
            self._log.critical(
                "Unable to store concentric street {streetName} "
                "({streetID}, ignore={ignoreDuplicates}) in event {event}: "
                "{error}",
                event=event, streetID=streetID, streetName=streetName,
                ignoreDuplicates=ignoreDuplicates, error=e,
            )
            raise

        self._log.info(
            "Stored concentric street {streetName} "
            "({streetID}, ignore={ignoreDuplicates}) in event {event}.",
            event=event, streetID=streetID, streetName=streetName,
            ignoreDuplicates=ignoreDuplicates,
        )


    def _storeIncidentType(
        _self, txn: Transaction, incidentType: str, hidden: bool
    ) -> None:
        self = cast(DatabaseStore, _self)

        txn.execute(
            self.query.createIncidentType.text,
            dict(incidentType=incidentType, hidden=hidden)
        )


    async def storeIncidentType(
        _self, incidentType: str, hidden: bool
    ) -> None:
        self = cast(DatabaseStore, _self)

        try:
            await self.runInteraction(
                _self._storeIncidentType,
                incidentType=incidentType, hidden=hidden,
            )
        except StorageError as e:
            self._log.critical(
                "Unable to store incident type {incidentType} "
                "(hidden={hidden}): {error}",
                incidentType=incidentType, hidden=hidden, error=e,
            )
            raise

        self._log.info(
            "Stored incident type {incidentType} (hidden={hidden}).",
            incidentType=incidentType, hidden=hidden,
        )


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
