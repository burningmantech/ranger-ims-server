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
File Elements
"""

__all__ = [
    "FileElement",
]

from twisted.web.template import Element, renderer, tags
from twisted.web.template import XMLFile



class FileElement(Element):
    def __init__(self, filePath):
        self.filePath = filePath
        self.loader = XMLFile(filePath)


    @renderer
    def icon(self, request, tag):
        return tags.link(
            rel="icon",
            href="/resources/ranger.png",
            type="image/png",
        )


    @renderer
    def stylesheet(self, request, tag):
        return tags.link(
            rel="stylesheet",
            media="screen",
            href="/resources/style.css",
            type="text/css",
        )
