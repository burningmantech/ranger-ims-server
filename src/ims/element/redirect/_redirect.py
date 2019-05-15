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
Redirect page.
"""

from attr import attrs

from hyperlink import URL

from twisted.python.filepath import FilePath
from twisted.web.iweb import IRequest, ITemplateLoader
from twisted.web.template import Tag, XMLFile, renderer

from .._element import BaseElement


__all__ = ()



@attrs(frozen=True, auto_attribs=True, kw_only=True, slots=True)
class RedirectPage(BaseElement):
    """
    Redirect page.
    """

    location: URL


    def _loader(self) -> ITemplateLoader:
        filePath = FilePath(__file__).parent().child("template.xhtml")
        return XMLFile(filePath)


    @renderer
    def destination(self, request: IRequest, tag: Tag) -> str:
        """
        JSON string: URL for the redirect destination.
        """
        return tag.fillSlots(destination_url=self.location.asText())
