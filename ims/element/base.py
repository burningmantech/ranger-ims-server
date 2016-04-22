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

from textwrap import dedent

from twisted.web.template import (
    Element as BaseElement, XMLFile, renderer, tags
)
from twisted.python.filepath import FilePath



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


    @renderer
    def head_common(self, request, tag=None):
        return (
            tags.meta(charset="utf-8"),
            tags.meta(
                name="viewport", content="width=device-width, initial-scale=1"
            ),
            tags.link(
                type="image/x-icon", rel="shortcut icon",
                href=self.service.favIconURL.asText(),
            ),
            tags.link(
                type="text/css", rel="stylesheet", media="screen",
                href=self.service.bootstrapURL.child(
                    u"css", u"bootstrap.min.css"
                ).asText(),
            ),
            tags.link(
                type="text/css", rel="stylesheet", media="screen",
                href=self.service.styleSheetURL.asText(),
            ),
            self.title(request, tags.title),
            tags.script(dedent(
                """
                var prefixURL = "{prefixURL}";
                """
                .format(
                    prefixURL=self.service.prefixURL.asText(),
                )
            )),
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
            tags.script(
                src=self.service.jqueryURL.child(u"jquery.min.js").asText(),
            ),
            tags.script(
                src=self.service.bootstrapURL.child(
                    u"js", u"bootstrap.min.js"
                ).asText(),
            ),
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
        def safe(obj):
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

        def redirectBack(url):
            # Set origin for redirect back to current page
            return url.set(u"o", request.uri.decode("utf-8")).asText()

        def url(url):
            return url.asText()

        def eventURL(url):
            # FIXME: replace <event>
            return url.asText()

        service = self.service

        tag.fillSlots(
            title=safe(self.elementTitle),

            user=safe(getattr(request, "user", u"(anonymous user)")),

            login_url=redirectBack(service.loginURL),
            logout_url=redirectBack(service.logoutURL),

            prefix_url=url(service.prefixURL),
            stylesheet_url=url(service.styleSheetURL),
            favicon_url=url(service.favIconURL),
            logo_url=url(service.logoURL),
            jquery_url=url(service.jqueryURL),
            bootstrap_url=url(service.bootstrapURL),
            datatables_url=url(service.datatablesURL),

            event_url=eventURL(service.eventURL),
            ping_url=eventURL(service.pingURL),
            personnel_url=eventURL(service.personnelURL),
            incident_types_url=eventURL(service.incidentTypesURL),
        )

        return tag
