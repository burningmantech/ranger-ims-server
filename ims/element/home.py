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
Home Page Element
"""

__all__ = [
    "HomePageElement",
]

from twisted.web.template import renderer, tags

from .base import BaseElement



class HomePageElement(BaseElement):

    def __init__(self, ims):
        BaseElement.__init__(
            self, ims, "home",
            "Ranger Incident Management System"
        )


    @renderer
    def events(self, request, tag):
        events = sorted(event for event in self.ims.storage)

        if events:
            return (
                tag.clone()(tags.a(event, href="/{}/queue".format(event)))
                for event in events
            )
        else:
            return tag("No events found.")
