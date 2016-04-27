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
Server root page.
"""

__all__ = [
    "RootPage",
]

from .base import Element, renderer, tags



class RootPage(Element):
    """
    Home page element
    """

    def __init__(self, service):
        Element.__init__(
            self, u"root", service,
            title=u"Ranger Incident Management System",
        )


    @renderer
    def events(self, request, tag):
        events = sorted(event for event in self.service.storage)

        if events:
            prefix = self.service.prefixURL.asText()
            return (
                tag.clone()(
                    tags.a(
                        event, href="{}/{}/queue".format(prefix, event)
                    )
                )
                for event in events
            )
        else:
            return tag("No events found.")
