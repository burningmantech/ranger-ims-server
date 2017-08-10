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
Incident page.
"""

from typing import Optional

from twisted.web.iweb import IRequest
from twisted.web.template import Tag, renderer

from ims.auth import Authorization
from ims.config import Configuration
from ims.ext.json import jsonFalse, jsonTextFromObject, jsonTrue
from ims.ext.klein import KleinRenderable
from ims.model import Event

from .._page import Page
from ..incident_template._incident_template import title


__all__ = ()



class IncidentPage(Page):
    """
    Incident page.
    """

    def __init__(
        self, config: Configuration, event: Event, number: Optional[int]
    ) -> None:
        super().__init__(config=config, title=title)
        self.event = event
        self.number = number


    @renderer
    def editing_allowed(self, request: IRequest, tag: Tag) -> KleinRenderable:
        """
        JSON boolean, true if editing is allowed.
        """
        if (request.authorizations & Authorization.writeIncidents):
            return jsonTrue
        else:
            return jsonFalse


    @renderer
    def event_id(self, request: IRequest, tag: Tag) -> KleinRenderable:
        """
        JSON string: event ID.
        """
        return jsonTextFromObject(self.event.id)


    @renderer
    def incident_number(self, request: IRequest, tag: Tag) -> KleinRenderable:
        """
        JSON integer: incident number.
        """
        return jsonTextFromObject(self.number)


    @renderer
    def incidents_url(self, request: IRequest, tag: Tag) -> KleinRenderable:
        """
        JSON string: URL for incidents endpoint for the event.
        """
        return jsonTextFromObject(
            self.config.urls.incidents.asText()
            .replace("<eventID>", self.event.id)
        )


    @renderer
    def view_incidents_url(
        self, request: IRequest, tag: Tag
    ) -> KleinRenderable:
        """
        JSON string: URL for incidents page for the event.
        """
        return jsonTextFromObject(
            self.config.urls.viewIncidents.asText()
            .replace("<eventID>", self.event.id)
        )


    @renderer
    async def concentric_street_name_by_id(
        self, request: IRequest, tag: Tag
    ) -> KleinRenderable:
        """
        JSON dictionary: concentric streets by ID.
        """
        namesByID = await self.config.store.concentricStreets(self.event)
        return jsonTextFromObject(namesByID)
