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

from typing import Any, ClassVar, FrozenSet, Mapping
from typing.io import BinaryIO

from attr import attrs

from twisted.logger import Logger

from ims.ext.json import (
    jsonTextFromObject, objectFromJSONBytesIO, objectFromJSONText
)
from ims.model import Event, EventAccess, EventData, IMSData, IncidentType
from ims.model.json import jsonObjectFromModelObject, modelObjectFromJSONObject

from .._abc import IMSDataStore

__all__ = ()



@attrs(frozen=True, auto_attribs=True, kw_only=True)
class JSONExporter(object):
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
        return jsonObjectFromModelObject(await self.imsData())


    async def imsData(self) -> IMSData:
        """
        Export IMS Data.
        """
        return IMSData(
            incidentTypes=(await self._incidentTypes()),
            events=frozenset([
                await self._eventData(event)
                for event in await self.store.events()
            ]),
        )


    async def _incidentTypes(self) -> FrozenSet[IncidentType]:
        """
        Export incident types.
        """
        allTypes = frozenset(
            await self.store.incidentTypes(includeHidden=True)
        )
        visibleTypes = frozenset(
            await self.store.incidentTypes(includeHidden=False)
        )

        return frozenset((
            IncidentType(name=name, hidden=(name not in visibleTypes))
            for name in allTypes
        ))


    async def _eventData(self, event: Event) -> EventData:
        """
        Export an event.
        """
        self._log.info("Exporting event {event}...", event=event)

        eventAccess = EventAccess(
            readers=frozenset(await self.store.readers(event)),
            writers=frozenset(await self.store.writers(event)),
            reporters=frozenset(await self.store.reporters(event)),
        )

        concentricStreets = dict(await self.store.concentricStreets(event))
        incidents = tuple(await self.store.incidents(event))
        incidentReports = tuple(await self.store.incidentReports(event))

        return EventData(
            event=event,
            access=eventAccess,
            concentricStreets=concentricStreets,
            incidents=incidents,
            incidentReports=incidentReports,
        )



@attrs(frozen=True, auto_attribs=True, kw_only=True)
class JSONImporter(object):
    """
    Incident Management System data store JSON importer.
    """

    _log: ClassVar[Logger] = Logger()

    store: IMSDataStore
    imsData: IMSData


    @classmethod
    def fromIO(
        cls, store: IMSDataStore, io: BinaryIO
    ) -> "JSONImporter":
        cls._log.info("Reading from JSON I/O...")
        return cls.fromJSON(store, objectFromJSONBytesIO(io))


    @classmethod
    def fromBytes(
        cls, store: IMSDataStore, jsonBytes: bytes
    ) -> "JSONImporter":
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


    async def storeData(self) -> None:
        raise NotImplementedError()
