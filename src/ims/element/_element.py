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

from functools import partial
from typing import Iterable

from attr import attrs

from twisted.python.filepath import FilePath
from twisted.python.reflect import namedModule
from twisted.web.iweb import IRequest, ITemplateLoader
from twisted.web.template import (
    Element as _Element, Tag, XMLFile, renderer, tags
)

from ims.auth import Authorization
from ims.config import Configuration
from ims.ext.json import jsonTextFromObject
from ims.ext.klein import KleinRenderable


__all__ = ()



@attrs(auto_attribs=True, kw_only=True)
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



@attrs(auto_attribs=True, kw_only=True)
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

        slots = dict(user=username)

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
        else:
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
        else:
            return tag(username)


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
        name = tag.attributes.pop("url", None)

        if name is None:
            raise ValueError("Rendered URL must have a url attribute")

        try:
            url = getattr(self.config.urls, name)
        except AttributeError:
            raise ValueError(f"Unknown URL name: {name}")

        text = url.asText()

        if tag.tagName == "json":
            return jsonTextFromObject(text)

        attributeName = tag.attributes.pop("attr", None)
        if attributeName is None:
            if tag.tagName in ("a", "link"):
                attributeName = "href"
            elif tag.tagName in ("script", "img"):
                attributeName = "src"
            else:
                raise ValueError("Rendered URL must have an attr attribute")

        if attributeName == "":
            return text
        else:
            tag.attributes[attributeName] = text
            return tag


    @renderer
    async def _events(
        self, request: IRequest, tag: Tag, reverse_order: bool = False
    ) -> KleinRenderable:
        if reverse_order:
            def order(i: Iterable) -> Iterable:
                return reversed(sorted(i))
        else:
            def order(i: Iterable) -> Iterable:
                return sorted(i)

        authorizationsForUser = partial(
            self.config.authProvider.authorizationsForUser, request.user
        )

        eventIDs = order([
            event.id for event in
            await self.config.store.events()
            if Authorization.readIncidents & await authorizationsForUser(event)
        ])

        if eventIDs:
            queue = self.config.urls.viewDispatchQueue.asText()
            return (
                tag.clone()(
                    tags.a(
                        eventID, href=queue.replace("<eventID>", eventID)
                    )
                )
                for eventID in eventIDs
            )
        else:
            return tag("No events found.")


    @renderer
    def events(self, request: IRequest, tag: Tag) -> KleinRenderable:
        """
        Repeat an element once for each event, embedding the event ID.
        """
        return self._events(request, tag)


    @renderer
    def events_reversed(self, request: IRequest, tag: Tag) -> KleinRenderable:
        """
        Repeat an element once for each event in reverse order, embedding the
        event ID.
        """
        return self._events(request, tag, reverse_order=True)


    @renderer
    async def events_list(
        self, request: IRequest, tag: Tag
    ) -> KleinRenderable:
        """
        JSON list of strings: events IDs.
        """
        return jsonTextFromObject(
            e.id for e in await self.config.store.events()
        )


    @renderer
    async def if_detached_reports(
        self, request: IRequest, tag: Tag
    ) -> KleinRenderable:
        """
        Render conditionally if there are detached incident reports.
        """
        if not (
            Authorization.readIncidentReports &
            await self.config.authProvider.authorizationsForUser(
                request.user, None
            )
        ):
            return ""

        for _incidentReport in (
            await self.config.store.detachedIncidentReports()
        ):
            return tag
        else:
            return ""
