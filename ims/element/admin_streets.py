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
Admin streets page.
"""

__all__ = [
    "AdminStreetsPage",
]

from ..data.json import textFromJSON
from ..service.urls import URLs
from .base import Element, renderer



class AdminStreetsPage(Element):
    """
    Admin streets page.
    """

    def __init__(self, service):
        Element.__init__(
            self, u"admin_streets", service,
            title=u"Admin: Event Concentric Streets",
        )


    @renderer
    def eventNames(self, request, tag):
        return textFromJSON(self.service.storage.events())


    @renderer
    def streets_url(self, request, tag):
        return textFromJSON(URLs.streets.asText())
