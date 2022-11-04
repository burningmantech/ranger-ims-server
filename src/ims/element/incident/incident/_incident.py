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


from attr import attrs
from klein import KleinRenderable
from twisted.web.iweb import IRequest
from twisted.web.template import Tag, renderer

from ims.auth import Authorization
from ims.ext.json import jsonFalse, jsonTextFromObject, jsonTrue
from ims.model import Event

from ...page import Page
from ..incident_template._incident_template import title


__all__ = ()


@attrs(auto_attribs=True, kw_only=True)
class IncidentPage(Page):
    """
    Incident page.
    """

    name: str = title
    event: Event
    number: int | None

    @renderer
    def editing_allowed(self, request: IRequest, tag: Tag) -> KleinRenderable:
        """
        JSON boolean, true if editing is allowed.
        """
        if (
            request.authorizations  # type: ignore[attr-defined]
            & Authorization.writeIncidents
        ):
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
    async def concentric_street_name_by_id(
        self, request: IRequest, tag: Tag
    ) -> KleinRenderable:
        """
        JSON dictionary: concentric streets by ID.
        """
        namesByID = await self.config.store.concentricStreets(self.event.id)
        return jsonTextFromObject(namesByID)
