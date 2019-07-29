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

from typing import Any, ClassVar, Iterable, Mapping

from attr import attrs

from twisted.logger import Logger

from ims.ext.json import jsonTextFromObject
from ims.model import Event, EventAccess, EventData, IMSData, IncidentType
from ims.model.json import jsonObjectFromModelObject

from .._abc import IMSDataStore

__all__ = ("JSONExporter")



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
        self._log.info("Encoding exported data as text...")
        return jsonTextFromObject(json)


    async def asJSON(self) -> Mapping[str, Any]:
        """
        Export data store as JSON.
        """
        self._log.info("Exporting data store as JSON...")
        return jsonObjectFromModelObject(await self.imsData())


    async def imsData(self) -> IMSData:
        """
        Export IMS Data.
        """
        return IMSData(
            incidentTypes=tuple(await self._incidentTypes()),
            events=[
                await self._eventData(event)
                for event in await self.store.events()
            ],
        )


    async def _incidentTypes(self) -> Iterable[IncidentType]:
        """
        Export incident types.
        """
        allTypes = tuple(await self.store.incidentTypes(includeHidden=True))
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
            readers=tuple(await self.store.readers(event)),
            writers=tuple(await self.store.writers(event)),
            reporters=tuple(await self.store.reporters(event)),
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
