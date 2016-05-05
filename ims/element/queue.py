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

from .base import Element, renderer

from ..json import textFromJSON
from ..data import concentricStreetNameByNumber



class DispatchQueuePage(Element):
    """
    Dispatch queue page.
    """

    columnNames = (
        u"#",
        u"Priority",
        u"Created",
        u"State",
        u"Rangers",
        u"Location",
        u"Types",
        u"Summary",
    )


    def __init__(self, service, storage, event):
        Element.__init__(
            self, u"queue", service,
            title=u"{} Dispatch Queue".format(event),
        )

        self.storage = storage
        self.event = event


    @renderer
    def table_headers(self, request, tag):
        return (
            tag.clone()(header)
            for header in self.columnNames
        )


    @renderer
    def data_url(self, request, tag):
        return (
            self.service.dispatchQueueDataURL.asText()
            .replace(u"<event>", unicode(self.event))
        )


    @renderer
    def view_incidents_url(self, request, tag):
        return (
            self.service.viewIncidentsURL.asText()
            .replace(u"<event>", unicode(self.event))
        )


    @renderer
    def concentric_street_name_by_number(self, request, tag):
        return textFromJSON(concentricStreetNameByNumber[self.event])
