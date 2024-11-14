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

from collections import OrderedDict
from collections.abc import Iterable, MutableMapping
from typing import cast

from attrs import mutable
from hyperlink import URL
from twisted.web.iweb import IRenderable, IRequest
from twisted.web.template import Tag, renderer, tags

from ims.config import Configuration

from .._element import Element
from .footer import FooterElement
from .header import HeaderElement
from .nav import NavElement


__all__ = ()


@mutable(kw_only=True)
class Page(Element):
    """
    XHTML page element.
    """

    config: Configuration
    name: str
    hideH1: bool = False

    def urlsFromImportSpec(self, spec: str) -> Iterable[URL]:
        """
        Given a string specifying desired imports, return the corresponding
        URLs.
        """
        urls = self.config.urls

        result: MutableMapping[str, URL] = OrderedDict()

        def add(name: str) -> None:
            if not name or name in result:
                return

            if name == "bootstrap":
                add("jquery")

            if name == "ims":
                add("jquery")

            try:
                result[name] = getattr(urls, f"{name}JS")
            except AttributeError:
                raise ValueError(
                    f"Invalid import {name!r} in spec {spec!r}"
                ) from None

            if name == "dataTables":
                add("dataTablesBootstrap")

        # All pages use Bootstrap
        add("bootstrap")
        add("urls")

        for name in spec.split(","):
            add(name.strip())

        return result.values()

    @renderer
    def title(self, request: IRequest, tag: Tag) -> IRenderable:
        """
        `<title>` element.
        """
        return tag.clone()(self.name)  # type: ignore[return-value]

    @renderer
    def head(self, request: IRequest, tag: Tag) -> IRenderable:
        """
        `<head>` element.
        """
        urls = self.config.urls

        children = tag.children
        tag.children = []

        imports = (
            tags.script(src=url.asText())
            for url in self.urlsFromImportSpec(
                cast(str, tag.attributes.get("imports", ""))
            )
        )

        if "imports" in tag.attributes:
            del tag.attributes["imports"]

        return tag(  # type: ignore[return-value]
            # Resource metadata
            tags.meta(charset="utf-8"),
            tags.meta(
                name="viewport", content="width=device-width, initial-scale=1"
            ),
            tags.link(
                type="image/png",
                rel="icon",
                href=urls.logo.asText(),
            ),
            tags.link(
                type="text/css",
                rel="stylesheet",
                href=urls.bootstrapCSS.asText(),
            ),
            tags.link(
                type="text/css",
                rel="stylesheet",
                href=urls.styleSheet.asText(),
            ),
            self.title(request, tags.title.clone()),
            # JavaScript resource imports
            imports,
            # Child elements
            children,
        )

    @renderer
    def container(self, request: IRequest, tag: Tag) -> IRenderable:
        """
        App container.
        """
        tag.children.insert(0, self.top(request))
        return tag(  # type: ignore[return-value]
            self.bottom(request), Class="container-fluid"
        )

    @renderer
    def top(self, request: IRequest, tag: Tag | None = None) -> IRenderable:
        """
        Top elements.
        """
        if self.hideH1:
            h1 = tags.h1.clone()(id="doc-title", hidden="true")
        else:
            h1 = tags.h1.clone()(id="doc-title")
        return (  # type: ignore[return-value]
            self.nav(request),
            self.header(request),
            self.title(request, h1),
        )

    @renderer
    def bottom(self, request: IRequest, tag: Tag | None = None) -> IRenderable:
        """
        Bottom elements.
        """
        return (self.footer(request),)  # type: ignore[return-value]

    @renderer
    def nav(self, request: IRequest, tag: Tag | None = None) -> IRenderable:
        """
        `<nav>` element.
        """
        return NavElement(config=self.config)

    @renderer
    def header(self, request: IRequest, tag: Tag | None = None) -> IRenderable:
        """
        `<header>` element.
        """
        return HeaderElement(config=self.config)

    @renderer
    def footer(self, request: IRequest, tag: Tag | None = None) -> IRenderable:
        """
        `<footer>` element.
        """
        return FooterElement(config=self.config)
