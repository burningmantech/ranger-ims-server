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

import sys
from typing import Any, ClassVar, Iterable, Mapping, Sequence

from attr import attrs

from twisted.logger import Logger

from ims.ext.json import jsonTextFromObject
from ims.model import Event
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


    @classmethod
    def main(cls, argv: Sequence[str] = sys.argv) -> None:
        """
        JSONExportCommand main entry point.
        """
        from ._command import JSONExportCommand
        JSONExportCommand.main(argv)


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
        return dict(
            incident_types=(await self._incidentTypes()),
            events=(await self._events()),
        )


    async def _incidentTypes(self) -> Iterable[Mapping[str, Any]]:
        """
        Export incident types.
        """
        self._log.info("Exporting incident types...")

        allTypes = tuple(await self.store.incidentTypes(includeHidden=True))
        visibleTypes = frozenset(
            await self.store.incidentTypes(includeHidden=False)
        )

        return (
            dict(name=incidentType, hidden=(incidentType in visibleTypes))
            for incidentType in allTypes
        )


    async def _events(self) -> Iterable[Mapping[str, Any]]:
        return [
            await self._event(event)
            for event in await self.store.events()
        ]


    async def _event(self, event: Event) -> Mapping[str, Any]:
        """
        Export an event.
        """
        self._log.info("Exporting event {event}...", event=event)
        return dict(
            id=event.id,
            access=(await self._access(event)),
            concentric_streets=(await self._concentricStreets(event)),
            incidents=(await self._incidents(event)),
            incident_reports=(await self._incidentReports(event)),
        )


    async def _access(self, event: Event) -> Mapping[str, Iterable[str]]:
        """
        Export event access.
        """
        self._log.info("Exporting access for event {event}...", event=event)
        return dict(
            readers=(await self.store.readers(event)),
            writers=(await self.store.writers(event)),
            reporters=(await self.store.reporters(event)),
        )


    async def _concentricStreets(self, event: Event) -> Mapping[str, str]:
        """
        Export event concentric streets.
        """
        self._log.info(
            "Exporting concentric streets for event {event}...", event=event
        )
        return (await self.store.concentricStreets(event))


    async def _incidents(self, event: Event) -> Iterable[Mapping[str, Any]]:
        """
        Export event incidents.
        """
        self._log.info("Exporting incidents for event {event}...", event=event)
        return (
            jsonObjectFromModelObject(incident)
            for incident in (await self.store.incidents(event))
        )


    async def _incidentReports(
        self, event: Event
    ) -> Iterable[Mapping[str, Any]]:
        """
        Export event incidents.
        """
        self._log.info(
            "Exporting incident reports for event {event}...", event=event
        )
        return (
            jsonObjectFromModelObject(incidentReport)
            for incidentReport in (await self.store.incidentReports(event))
        )
