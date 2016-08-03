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

__all__ = [
    "DispatchQueuePage",
]

from ..data.json import textFromJSON
from ..service.urls import URLs
from ..service.auth import Authorization

from .base import Element, renderer



class DispatchQueuePage(Element):
    """
    Dispatch queue page.
    """

    def __init__(self, service, event):
        Element.__init__(
            self, u"queue", service,
            title=u"{} Dispatch Queue".format(event),
        )

        self.event = event


    @renderer
    def editing_allowed(self, request, tag):
        if (request.authorizations & Authorization.writeIncidents):
            return textFromJSON(True)
        else:
            return textFromJSON(False)


    @renderer
    def event_id(self, request, tag):
        return textFromJSON(self.event)


    @renderer
    def template_url(self, request, tag):
        return textFromJSON(URLs.viewDispatchQueueTemplate.asText())

    @renderer
    def data_url(self, request, tag):
        return textFromJSON(
            URLs.incidents.asText()
            .replace(u"<event>", unicode(self.event))
        )


    @renderer
    def view_incidents_url(self, request, tag):
        return textFromJSON(
            URLs.viewIncidents.asText()
            .replace(u"<event>", unicode(self.event))
        )


    @renderer
    def concentric_street_name_by_id(self, request, tag):
        namesByID = self.service.storage.concentricStreetsByID(self.event)
        return textFromJSON(namesByID)
