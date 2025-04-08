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
Element base classes.
"""

from typing import cast
from unittest.mock import sentinel

from attrs import mutable
from klein import KleinRenderable
from twisted.python.filepath import FilePath
from twisted.python.reflect import namedModule
from twisted.web.iweb import IRequest, ITemplateLoader
from twisted.web.template import Element as _Element
from twisted.web.template import Tag, XMLFile, renderer

from ims.config import Configuration
from ims.ext.json_ext import jsonFalse, jsonTextFromObject, jsonTrue


__all__ = ()


@mutable(kw_only=True)
class BaseElement(_Element):
    """
    XHTML element.
    """

    def __attrs_post_init__(self) -> None:
        super().__init__(loader=self._loader())

    def _loader(self) -> ITemplateLoader:
        module = namedModule(self.__class__.__module__)
        filePath = FilePath(module.__file__).parent().child("template.xhtml")
        return XMLFile(filePath)


@mutable(kw_only=True)
class Element(BaseElement):
    """
    XHTML element.
    """

    config: Configuration

    ##
    # Main document elements
    ##

    @renderer
    def root(self, request: IRequest, tag: Tag) -> KleinRenderable:
        """
        Root element.
        """
        user = getattr(request, "user", None)
        if user is None:
            username = "(anonymous user)"
        else:
            try:
                username = user.shortNames[0]
            except IndexError:
                username = "* NO USER NAME *"

        slots = {"user": username}

        tag.fillSlots(**slots)

        return tag

    ##
    # Logged in state
    ##

    def isAuthenticated(self, request: IRequest) -> bool:
        return getattr(request, "user", None) is not None

    def isAdmin(self, request: IRequest) -> bool:
        user = getattr(request, "user", None)

        if user is not None:
            for shortName in user.shortNames:
                if shortName in self.config.imsAdmins:
                    return True

        return False

    @renderer
    def if_logged_in(self, request: IRequest, tag: Tag) -> KleinRenderable:
        """
        Render conditionally if the user is logged in.
        """
        if self.isAuthenticated(request):
            return tag
        return ""

    @renderer
    def if_not_logged_in(self, request: IRequest, tag: Tag) -> KleinRenderable:
        """
        Render conditionally if the user is not logged in.
        """
        if self.isAuthenticated(request):
            return ""
        return tag

    @renderer
    def if_admin(self, request: IRequest, tag: Tag) -> KleinRenderable:
        """
        Render conditionally if the user is an admin.
        """
        if self.isAdmin(request):
            return tag
        return ""

    @renderer
    def logged_in_user(self, request: IRequest, tag: Tag) -> KleinRenderable:
        """
        Embed the logged in user into an element content.
        """
        user = getattr(request, "user", None)
        if user is None:
            username = "(anonymous user)"
        else:
            try:
                username = user.shortNames[0]
            except IndexError:
                username = "* NO USER NAME *"

        if tag.tagName == "text":
            return username
        return tag(username)

    @renderer
    def deployment_warning(self, request: IRequest, tag: Tag) -> KleinRenderable:
        deployment = self.config.deployment.lower()
        if deployment == "production":
            return ""
        return tag(f"This is not production. This is a {deployment} IMS server.")

    ##
    # Data
    ##

    @renderer
    def url(self, request: IRequest, tag: Tag) -> KleinRenderable:
        """
        Look up a URL with the name specified by the given tag's C{"url"}
        attribute, which will be removed.
        If the tag has an C{"attr"} attribute, remove it and add the URL to the
        tag in the attribute named by the (removed) C{"attr"} attribute and
        return the tag.
        For C{"a"} tags, C{"attr"} defaults to C{"href"}.
        For C{"img"} tags, C{"attr"} defaults to C{"src"}.
        If the C{"attr"} attribute is defined C{""}, return the URL as text.
        """
        name = cast("str", tag.attributes.pop("url", sentinel.name))

        if name is sentinel.name:
            raise ValueError("Rendered URL must have a url attribute")

        try:
            url = getattr(self.config.urls, name)
        except AttributeError:
            raise ValueError(f"Unknown URL name: {name}") from None

        text = cast("str", url.asText())

        if tag.tagName == "json":
            return jsonTextFromObject(text)

        attributeName = cast("str", tag.attributes.pop("attr", sentinel.name))
        if attributeName is sentinel.name:
            if tag.tagName in ("a", "link"):
                attributeName = "href"
            elif tag.tagName in ("script", "img"):
                attributeName = "src"
            else:
                raise ValueError("Rendered URL must have an attr attribute")

        if attributeName == "":
            return text

        tag.attributes[attributeName] = text
        return tag

    @renderer
    def file_attachments_allowed(self, request: IRequest, tag: Tag) -> KleinRenderable:
        """
        Identifies if file attachment uploads are allowed by the server.
        """
        return (
            jsonFalse
            if self.config.attachmentsStoreType.lower() == "none"
            else jsonTrue
        )
