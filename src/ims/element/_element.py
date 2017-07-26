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

from twisted.python.filepath import FilePath
from twisted.python.reflect import namedModule
from twisted.web.iweb import IRequest, ITemplateLoader
from twisted.web.template import (
    Element as BaseElement, Tag, XMLFile, renderer, tags
)

from ims.ext.klein import KleinRenderable


__all__ = ()



class Element(BaseElement):
    """
    XHTML element.
    """

    def __init__(self) -> None:
        super().__init__(loader=self._loader())


    def _loader(self) -> ITemplateLoader:
        module = namedModule(self.__class__.__module__)
        filePath = FilePath(module.__file__)
        if filePath.isfile():
            filePath = filePath.parent()
        filePath = filePath.child("template.xhtml")
        return XMLFile(filePath)



class Page(Element):
    """
    XHTML page element.
    """

    def __init__(self, urls: type, title: str) -> None:
        super().__init__()
        self.urls = urls
        self.titleText = title


    @renderer
    def root(self, request: IRequest, tag: Tag = tags.html) -> KleinRenderable:
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


    @renderer
    def title(
        self, request: IRequest, tag: Tag = tags.title
    ) -> KleinRenderable:
        """
        `<title>` element.
        """
        if self.titleText is None:
            titleText = ""
        else:
            titleText = self.titleText

        return tag(titleText)


    @renderer
    def head(self, request: IRequest, tag: Tag = tags.head) -> KleinRenderable:
        """
        <head> element.
        """
        urls = self.urls

        children = tag.children
        tag.children = []

        return tag(
            tags.meta(charset="utf-8"),
            tags.meta(
                name="viewport", content="width=device-width, initial-scale=1"
            ),
            tags.link(
                type="image/png", rel="icon",
                href=urls.logo.asText(),
            ),
            tags.link(
                type="text/css", rel="stylesheet", media="screen",
                href=urls.bootstrapCSS.asText(),
            ),
            tags.link(
                type="text/css", rel="stylesheet", media="screen",
                href=urls.styleSheet.asText(),
            ),
            tags.script(src=urls.jqueryJS.asText()),
            tags.script(src=urls.bootstrapJS.asText()),
            self.title(request),
            children,
        )


    @renderer
    def container(
        self, request: IRequest, tag: Tag = tags.div
    ) -> KleinRenderable:
        """
        App container.
        """
        tag.children.insert(0, self.top(request))
        return tag(self.bottom(request), Class="container-fluid")


    @renderer
    def top(self, request: IRequest, tag: Tag = tags.div) -> KleinRenderable:
        """
        Top elements.
        """
        return (
            self.nav(request),
            self.header(request),
            self.title(request, tags.h1),
        )


    @renderer
    def bottom(
        self, request: IRequest, tag: Tag = tags.div
    ) -> KleinRenderable:
        """
        Bottom elements.
        """
        return (self.footer(request),)


    @renderer
    def nav(self, request: IRequest, tag: Tag = tags.nav) -> KleinRenderable:
        """
        <nav> element.
        """
        return ""
        # return Element("base_nav", self.service)


    @renderer
    def header(
        self, request: IRequest, tag: Tag = tags.header
    ) -> KleinRenderable:
        """
        <header> element.
        """
        return ""
        # return Element("base_header", self.service)


    @renderer
    def footer(
        self, request: IRequest, tag: Tag = tags.footer
    ) -> KleinRenderable:
        """
        <footer> element.
        """
        return ""
        # return Element("base_footer", self.service)
