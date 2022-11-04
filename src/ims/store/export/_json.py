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
Incident Management System data store export.
"""

from collections.abc import Iterable, Mapping
from typing import Any, BinaryIO, ClassVar, cast

from attr import attrs
from twisted.logger import Logger

from ims.ext.json import (
    jsonTextFromObject,
    objectFromJSONBytesIO,
    objectFromJSONText,
)
from ims.model import Event, EventAccess, EventData, IMSData, IncidentType
from ims.model.json import jsonObjectFromModelObject, modelObjectFromJSONObject

from .._abc import IMSDataStore


__all__ = ()


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class JSONExporter:
    """
    Incident Management System data store JSON exporter.
    """

    _log: ClassVar[Logger] = Logger()

    store: IMSDataStore

    async def asBytes(self) -> bytes:
        """
        Export data store as bytes.
        """
        text = await self.asText()
        self._log.info("Encoding exported data as bytes...")
        return text.encode("utf-8")

    async def asText(self) -> str:
        """
        Export data store as text.
        """
        json = await self.asJSON()
        self._log.info("Encoding exported data as JSON text...")
        return jsonTextFromObject(json)

    async def asJSON(self) -> Mapping[str, Any]:
        """
        Export data store as JSON.
        """
        self._log.info("Exporting data store as JSON objects...")
        return cast(
            Mapping[str, Any], jsonObjectFromModelObject(await self.imsData())
        )

    async def imsData(self) -> IMSData:
        """
        Export IMS Data.
        """
        return IMSData(
            incidentTypes=(await self._incidentTypes()),
            events=[
                await self._eventData(event)
                for event in await self.store.events()
            ],
        )

    async def _incidentTypes(self) -> Iterable[IncidentType]:
        """
        Export incident types.
        """
        allTypes = frozenset(await self.store.incidentTypes(includeHidden=True))
        visibleTypes = frozenset(
            await self.store.incidentTypes(includeHidden=False)
        )

        return (
            IncidentType(name=name, hidden=(name not in visibleTypes))
            for name in allTypes
        )

    async def _eventData(self, event: Event) -> EventData:
        """
        Export an event.
        """
        self._log.info("Exporting event {event}...", event=event)

        eventAccess = EventAccess(
            readers=(await self.store.readers(event.id)),
            writers=(await self.store.writers(event.id)),
            reporters=(await self.store.reporters(event.id)),
        )

        concentricStreets = await self.store.concentricStreets(event.id)
        incidents = await self.store.incidents(event.id)
        incidentReports = await self.store.incidentReports(event.id)

        return EventData(
            event=event,
            access=eventAccess,
            concentricStreets=concentricStreets,
            incidents=incidents,
            incidentReports=incidentReports,
        )


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class JSONImporter:
    """
    Incident Management System data store JSON importer.
    """

    _log: ClassVar[Logger] = Logger()

    store: IMSDataStore | None
    imsData: IMSData

    @classmethod
    def fromIO(cls, store: IMSDataStore, io: BinaryIO) -> "JSONImporter":
        cls._log.info("Reading from JSON I/O...")
        return cls.fromJSON(store, objectFromJSONBytesIO(io))

    @classmethod
    def fromBytes(cls, store: IMSDataStore, jsonBytes: bytes) -> "JSONImporter":
        cls._log.info("Reading from JSON bytes...")
        return cls.fromText(store, jsonBytes.decode("utf-8"))

    @classmethod
    def fromText(cls, store: IMSDataStore, jsonText: str) -> "JSONImporter":
        cls._log.info("Reading from JSON text...")
        return cls.fromJSON(store, objectFromJSONText(jsonText))

    @classmethod
    def fromJSON(
        cls, store: IMSDataStore, json: Mapping[str, Any]
    ) -> "JSONImporter":
        """
        Import JSON.
        """
        cls._log.info("Reading from JSON objects...")
        imsData = modelObjectFromJSONObject(json, IMSData)
        return cls(store=store, imsData=imsData)

    async def _storeIncidentTypes(self) -> None:
        store = self.store

        assert store is not None

        existingIncidentTypes = frozenset(
            await store.incidentTypes(includeHidden=True)
        )

        for incidentType in self.imsData.incidentTypes:
            if incidentType.name in existingIncidentTypes:
                self._log.info(
                    "Not importing existing incident type: {incidentType}",
                    incidentType=incidentType,
                )
            else:
                await store.createIncidentType(
                    incidentType.name, incidentType.hidden
                )

    async def _storeEventAccess(self, eventData: EventData) -> None:
        store = self.store
        event = eventData.event
        eventAccess = eventData.access

        assert store is not None

        await store.setReaders(event.id, eventAccess.readers)
        await store.setWriters(event.id, eventAccess.writers)
        await store.setReporters(event.id, eventAccess.reporters)

    async def _storeConcentricStreets(self, eventData: EventData) -> None:
        store = self.store
        event = eventData.event

        assert store is not None

        existingStreetIDs = frozenset(
            (await store.concentricStreets(event.id)).keys()
        )

        for streetID, streetName in eventData.concentricStreets.items():
            if streetID in existingStreetIDs:
                self._log.info(
                    "Not importing existing street {streetID} "
                    "into event {event}",
                    event=eventData.event,
                    streetID=streetID,
                )
            else:
                await store.createConcentricStreet(
                    event.id, streetID, streetName
                )

    async def _storeIncidents(self, eventData: EventData) -> None:
        store = self.store

        assert store is not None

        existingIncidentNumbers = frozenset(
            incident.number
            for incident in await store.incidents(eventData.event.id)
        )

        for incident in eventData.incidents:
            if incident.number in existingIncidentNumbers:
                self._log.info(
                    "Not importing existing incident #{number} "
                    "into event {event}",
                    event=eventData.event,
                    number=incident.number,
                )
            else:
                await store.importIncident(incident)

    async def _storeIncidentReports(self, eventData: EventData) -> None:
        store = self.store

        assert store is not None

        existingIncidentReportNumbers = frozenset(
            incidentReport.number
            for incidentReport in await store.incidentReports(
                eventData.event.id
            )
        )

        for incidentReport in eventData.incidentReports:
            if incidentReport.number in existingIncidentReportNumbers:
                self._log.info(
                    "Not importing existing incident report #{number} "
                    "into event {event}",
                    event=eventData.event,
                    number=incidentReport.number,
                )
            else:
                await store.importIncidentReport(incidentReport)

    async def storeData(self) -> None:
        store = self.store

        if store is None:
            raise RuntimeError("No data store")

        imsData = self.imsData

        await self._storeIncidentTypes()

        existingEvents = frozenset(await store.events())

        for eventData in imsData.events:
            event = eventData.event

            if event in existingEvents:
                self._log.info(
                    "Not creating existing event: {event}",
                    event=event,
                )
            else:
                await store.createEvent(event)

            await self._storeEventAccess(eventData)
            await self._storeConcentricStreets(eventData)
            await self._storeIncidents(eventData)
            await self._storeIncidentReports(eventData)
