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

__all__ = [
    "Element",
    "XMLFile",
    "renderer",
    "tags",
]

from twisted.web.template import (
    Element as BaseElement, XMLFile, renderer, tags
)
from twisted.python.filepath import FilePath
from twext.python.types import MappingProxyType



class Element(BaseElement):
    """
    Element.
    """

    def __init__(self, name, service, title=None, loader=None, tag=tags.html):
        BaseElement.__init__(self, loader=self._loader(name))

        self.elementName = name
        self.elementTitle = title
        self.service = service
        self.tag = tag


    def _loader(self, name):
        return XMLFile(
            FilePath(__file__).parent().child(u"{}.xhtml".format(name))
        )


    ##
    # Common elements
    ##


    # FIXME: Move below to xhtml
    @renderer
    def head_common(self, request, tag=None):
        return (
            tags.meta(charset="utf-8"),
            tags.meta(
                name="viewport", content="width=device-width, initial-scale=1"
            ),
            tags.link(
                type="image/png", rel="icon",
                href=self.service.logoURL.asText(),
            ),
            tags.link(
                type="text/css", rel="stylesheet", media="screen",
                href=self.service.bootstrapCSSURL.asText(),
            ),
            tags.link(
                type="text/css", rel="stylesheet", media="screen",
                href=self.service.styleSheetURL.asText(),
            ),
            tags.script(src=self.service.jqueryJSURL.asText()),
            tags.script(src=self.service.bootstrapJSURL.asText()),
            self.title(request, tags.title),
        )


    @renderer
    def container(self, request, tag):
        tag.children.insert(0, self.top(request))
        return tag(self.bottom(request), **{"class": "container-fluid"})


    @renderer
    def top(self, request, tag=None):
        return (
            self.nav(request),
            self.header(request),
            self.title(request),
        )


    @renderer
    def bottom(self, request, tag=None):
        return (
            self.footer(request),
        )


    @renderer
    def title(self, request, tag=None):
        if self.elementTitle is None:
            return u""
        else:
            if tag is None:
                tag = tags.h1()
            return tag(self.elementTitle)


    @renderer
    def nav(self, request, tag=None):
        return Element(u"base_nav", self.service)


    @renderer
    def header(self, request, tag=None):
        return Element(u"base_header", self.service)


    @renderer
    def footer(self, request, tag=None):
        return Element(u"base_footer", self.service)


    ##
    # Common data
    ##


    @renderer
    def if_logged_in(self, request, tag):
        if getattr(request, "user", None) is None:
            return u""
        else:
            return tag


    @renderer
    def root(self, request, tag):
        service = self.service

        def redirectBack(url):
            # Set origin for redirect back to current page
            return url.set(u"o", request.uri.decode("utf-8")).asText()

        slots = dict(self.fixedSlots)

        slots.update(dict(
            user=objectAsUnicode(getattr(request, "user", u"(anonymous user)")),

            login_url=redirectBack(service.loginURL),
            logout_url=redirectBack(service.logoutURL),
        ))

        tag.fillSlots(**slots)

        return tag


    @property
    def fixedSlots(self):
        if not hasattr(self, "_fixedSlots"):
            service = self.service

            self._fixedSlots = MappingProxyType(dict(
                title=objectAsUnicode(self.elementTitle),

                prefix_url=service.prefixURL.asText(),
                stylesheet_url=service.styleSheetURL.asText(),
                logo_url=service.logoURL.asText(),

                jquery_base_url=service.jqueryBaseURL.asText(),
                jquery_js_url=service.jqueryJSURL.asText(),
                jquery_map_url=service.jqueryMapURL.asText(),
                bootstrap_base_url=service.bootstrapBaseURL.asText(),
                bootstrap_css_url=service.bootstrapCSSURL.asText(),
                bootstrap_js_url=service.bootstrapJSURL.asText(),
                datatables_base_url=service.dataTablesBaseURL.asText(),
                datatables_js_url=service.dataTablesJSURL.asText(),
                datatables_bootstrap_css_url=(
                    service.dataTablesBootstrapCSSURL.asText()
                ),
                datatables_bootstrap_js_url=(
                    service.dataTablesBootstrapJSURL.asText()
                ),
                moment_js_url=service.momentJSURL.asText(),

                ims_js_url=service.imsJSURL.asText(),
            ))

        return self._fixedSlots



def objectAsUnicode(obj):
    if obj is None:
        return u"* NONE *"
    else:
        try:
            return unicode(obj)
        except:
            try:
                return repr(obj).decode("utf-8")
            except:
                return u"* ERROR *"
