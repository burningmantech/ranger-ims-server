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
Base element class.
"""

from twisted.python.filepath import FilePath
from twisted.web.template import (
    Element as BaseElement, XMLFile, renderer, tags
)

from ims.application import URLs
from ims.ext.json import jsonTextFromObject


__all__ = (
    "Element",
    "XMLFile",
    "renderer",
    "tags",
)



class Element(BaseElement):
    """
    Element.
    """

    def __init__(self, name, service, title=None, loader=None, tag=tags.html):
        """
        @param name: The template name.
        @param service: The service.
        @param title: The page title.
        @param loader: The page loader.
        @param tag: The element tag.
        """
        BaseElement.__init__(self, loader=self._loader(name))

        self.elementName = name
        self.elementTitle = str(title)
        self.service = service
        self.tag = tag


    def _loader(self, name):
        return XMLFile(
            FilePath(__file__).parent().child("{}.xhtml".format(name))
        )


    ##
    # Common elements
    ##

    @renderer
    def title(self, request, tag):
        """
        <title> element.
        """
        if self.elementTitle is None:
            title = ""
        else:
            title = self.elementTitle

        return tag(title)


    # FIXME: Move below to xhtml
    @renderer
    def head(self, request, tag=None):
        """
        <head> element.
        """
        if tag is None:
            children = ()
            tag = tags.head
        else:
            children = tag.children
            tag.children = []

        return tag(
            tags.meta(charset="utf-8"),
            tags.meta(
                name="viewport", content="width=device-width, initial-scale=1"
            ),
            tags.link(
                type="image/png", rel="icon",
                href=URLs.logo.asText(),
            ),
            tags.link(
                type="text/css", rel="stylesheet", media="screen",
                href=URLs.bootstrapCSS.asText(),
            ),
            tags.link(
                type="text/css", rel="stylesheet", media="screen",
                href=URLs.styleSheet.asText(),
            ),
            tags.script(src=URLs.jqueryJS.asText()),
            tags.script(src=URLs.bootstrapJS.asText()),
            self.title(request, tags.title),
            children,
        )


    # FIXME: Move below to xhtml
    @renderer
    def container(self, request, tag):
        """
        App container.
        """
        tag.children.insert(0, self.top(request))
        return tag(self.bottom(request), **{"class": "container-fluid"})


    @renderer
    def top(self, request, tag=None):
        """
        Top elements.
        """
        return (
            self.nav(request),
            self.header(request),
            self.title(request, tags.h1),
        )


    @renderer
    def bottom(self, request, tag=None):
        """
        Bottom elements.
        """
        return (
            self.footer(request),
        )


    @renderer
    def nav(self, request, tag=None):
        """
        <nav> element.
        """
        return Element("base_nav", self.service)


    @renderer
    def header(self, request, tag=None):
        """
        <header> element.
        """
        return Element("base_header", self.service)


    @renderer
    def footer(self, request, tag=None):
        """
        <footer> element.
        """
        return Element("base_footer", self.service)


    ##
    # Logged in state
    ##

    @renderer
    def if_logged_in(self, request, tag):
        """
        Render conditionally if the user is logged in.
        """
        if getattr(request, "user", None) is None:
            return ""
        return tag


    @renderer
    def if_not_logged_in(self, request, tag):
        """
        Render conditionally if the user is not logged in.
        """
        if getattr(request, "user", None) is not None:
            return ""
        return tag


    @renderer
    def if_admin(self, request, tag):
        """
        Render conditionally if the user is an admin.
        """
        user = getattr(request, "user", None)

        if user is not None and self.service is not None:
            for shortName in user.shortNames:
                if shortName in self.service.config.IMSAdmins:
                    return tag

        return ""


    @renderer
    def logged_in_user(self, request, tag):
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
    # Common data
    ##

    @renderer
    def root(self, request, tag):
        """
        Root element.
        """
        def redirectBack(url):
            # Set origin for redirect back to current page
            return url.set("o", request.uri.decode("utf-8")).asText()

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


    @renderer
    async def _events(self, request, tag, reverse_order=False):
        if self.service is None:
            events = ()
        else:
            events = sorted(
                event.id for event in await self.service.storage.events()
            )

        if reverse_order:
            events = reversed(events)

        if events:
            queue = URLs.viewDispatchQueue.asText()
            return (
                tag.clone()(
                    tags.a(
                        event, href=queue.replace("<eventID>", event)
                    )
                )
                for event in events
            )
        else:
            return tag("No events found.")


    @renderer
    def events(self, request, tag):
        """
        Repeat an element once for each event, embedding the event ID.
        """
        return self._events(request, tag)


    @renderer
    def events_reversed(self, request, tag):
        """
        Repeat an element once for each event in reverse order, embedding the
        event ID.
        """
        return self._events(request, tag, reverse_order=True)


    ##
    # URLs
    ##

    @renderer
    def url(self, request, tag):
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
            raise RuntimeError("Rendered URL must have a url attribute")

        try:
            url = getattr(URLs, name)
        except AttributeError:
            raise RuntimeError("Unknown URL name: {}".format(name))

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
                raise RuntimeError("Rendered URL must have an attr attribute")

        if attributeName == "":
            return text
        else:
            tag.attributes[attributeName] = text
            return tag
