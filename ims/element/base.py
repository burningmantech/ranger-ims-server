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
Base Element
"""

__all__ = [
    "BaseElement",
]

from twisted.web.template import renderer

from .file import FileElement



class BaseElement(FileElement):
    def __init__(self, ims, template_name, title):
        FileElement.__init__(
            self,
            ims.config.Resources.child("{0}.xhtml".format(template_name))
        )

        self.ims = ims
        self.template_name = template_name
        self._title = title


    @renderer
    def user(self, request, tag):
        return tag(self.ims.user)


    @renderer
    def title(self, request, tag):
        return tag(self._title)
