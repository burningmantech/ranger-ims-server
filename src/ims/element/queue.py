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
Dispatch queue page.
"""

from .base import Element, renderer
from ..legacy.data.json import jsonTextFromObject
from ..service.auth import Authorization
from ..service.urls import URLs


__all__ = (
    "DispatchQueuePage",
)



class DispatchQueuePage(Element):
    """
    Dispatch queue page.
    """

    def __init__(self, service, event):
        """
        @param service: The service.
        @param: The event ID.
        """
        Element.__init__(
            self, "queue", service,
            title="{} Dispatch Queue".format(event),
        )

        self.event = event


    @renderer
    def editing_allowed(self, request, tag):
        """
        JSON boolean, true if editing is allowed.
        """
        if (request.authorizations & Authorization.writeIncidents):
            return jsonTextFromObject(True)
        else:
            return jsonTextFromObject(False)


    @renderer
    def event_id(self, request, tag):
        """
        JSON string: event ID.
        """
        return jsonTextFromObject(self.event.id)


    @renderer
    def data_url(self, request, tag):
        """
        JSON string: URL for incidents endpoint for the event.
        """
        return jsonTextFromObject(
            URLs.incidents.asText()
            .replace("<eventID>", self.event.id)
        )


    @renderer
    def view_incidents_url(self, request, tag):
        """
        JSON string: URL for incidents page for the event.
        """
        return jsonTextFromObject(
            URLs.viewIncidents.asText()
            .replace("<eventID>", self.event.id)
        )


    @renderer
    def concentric_street_name_by_id(self, request, tag):
        """
        JSON dictionary: concentric streets by ID.
        """
        namesByID = self.service.storage.concentricStreetsByID(self.event)
        return jsonTextFromObject(namesByID)
