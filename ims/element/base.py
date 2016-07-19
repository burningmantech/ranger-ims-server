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

from ..service.urls import URLs



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
    def head(self, request, tag=None):
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
        return tag


    @renderer
    def if_admin(self, request, tag):
        user = getattr(request, "user", None)

        if user is None:
            return u""

        for shortName in user.shortNames:
            if shortName in self.service.config.IMSAdmins:
                return tag

        return u""


    @renderer
    def root(self, request, tag):
        def redirectBack(url):
            # Set origin for redirect back to current page
            return url.set(u"o", request.uri.decode("utf-8")).asText()

        user = getattr(request, "user", None)
        if user is None:
            username = u"(anonymous user)"
        else:
            try:
                username = user.shortNames[0]
            except IndexError:
                username = u"* NO USER NAME *"

        slots = dict(self.baseSlots)

        slots.update(dict(
            user=username,

            login_url=redirectBack(URLs.login),
            logout_url=redirectBack(URLs.logout),
        ))

        tag.fillSlots(**slots)

        return tag


    @renderer
    def _events(self, request, tag, reverse_order=False):
        events = sorted(event for event in self.service.storage.events())

        if reverse_order:
            events = reversed(events)

        if events:
            prefix = URLs.viewEvents.asText()
            return (
                tag.clone()(
                    tags.a(
                        event, href="{}/{}/queue".format(prefix, event)
                    )
                )
                for event in events
            )
        else:
            return tag("No events found.")


    @renderer
    def events(self, request, tag):
        return self._events(request, tag)


    @renderer
    def events_reversed(self, request, tag):
        return self._events(request, tag, reverse_order=True)


    @property
    def baseSlots(self):
        if not hasattr(self, "_baseSlots"):
            self._baseSlots = MappingProxyType(dict(
                title=objectAsUnicode(self.elementTitle),

                prefix_url=URLs.prefix.asText(),
                stylesheet_url=URLs.styleSheet.asText(),
                logo_url=URLs.logo.asText(),

                jquery_base_url=URLs.jqueryBase.asText(),
                jquery_js_url=URLs.jqueryJS.asText(),
                jquery_map_url=URLs.jqueryMap.asText(),
                bootstrap_base_url=URLs.bootstrapBase.asText(),
                bootstrap_css_url=URLs.bootstrapCSS.asText(),
                bootstrap_js_url=URLs.bootstrapJS.asText(),
                datatables_base_url=URLs.dataTablesBase.asText(),
                datatables_js_url=URLs.dataTablesJS.asText(),
                datatables_bootstrap_css_url=(
                    URLs.dataTablesbootstrapCSS.asText()
                ),
                datatables_bootstrap_js_url=(
                    URLs.dataTablesbootstrapJS.asText()
                ),
                moment_js_url=URLs.momentJS.asText(),

                ims_js_url=URLs.imsJS.asText(),

                admin_url=URLs.admin.asText(),
                admin_js_url=URLs.adminJS.asText(),

                admin_types_url=URLs.adminIncidentTypes.asText(),
                admin_types_js_url=URLs.adminIncidentTypesJS.asText(),

                admin_acl_url=URLs.adminAccessControl.asText(),
                admin_acl_js_url=URLs.adminAccessControlJS.asText(),

                admin_streets_url=URLs.adminStreets.asText(),
                admin_streets_js_url=URLs.adminStreetsJS.asText(),

                queue_js_url=URLs.viewDispatchQueueJS.asText(),
                incident_js_url=URLs.viewIncidentNumberJS.asText(),
                incident_report_js_url=URLs.viewIncidentReportJS.asText(),
            ))

        return self._baseSlots



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
