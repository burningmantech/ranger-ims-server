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
Protocol bits
"""

__all__ = [
    "IncidentManagementSystem",
]

from twisted.python.zippath import ZipArchive
from twisted.internet.defer import Deferred
from twisted.web import http
from twisted.web.static import File

from klein import Klein

from .json import JSON, json_as_text, json_from_file
from .json import ranger_as_json, incident_as_json, incident_from_json
from .data import Incident
from .edit import edit_incident
from .sauce import url_for, set_response_header
from .sauce import http_sauce
from .sauce import HeaderName, ContentType
from .element.file import FileElement
from .element.home import HomePageElement
from .element.queue import DispatchQueueElement
from .element.incident import IncidentElement
# from .element.report_daily import DailyReportElement
# from .element.report_shift import ShiftReportElement
from .element.util import incidents_from_query
from .util import http_download



class IncidentManagementSystem(object):
    """
    Incident Management System
    """
    app = Klein()

    protocol_version = "0.0"


    def __init__(self, config):
        self.config = config
        self.avatarId = None
        self.storage = config.storage
        self.dms = config.dms


    #
    # JSON endpoints
    #

    @app.route("/ping", methods=("GET",))
    @app.route("/ping/", methods=("GET",))
    @http_sauce
    def ping(self, request):
        ack = "ack"
        set_response_header(
            request, HeaderName.etag, ack
        )
        set_response_header(
            request, HeaderName.contentType, ContentType.JSON
        )
        return json_as_text(ack)


    @app.route("/rangers", methods=("GET",))
    @app.route("/rangers/", methods=("GET",))
    @app.route("/personnel", methods=("GET",))
    @app.route("/personnel/", methods=("GET",))
    @http_sauce
    def list_rangers(self, request):
        def gotPersonnel(personnel):
            set_response_header(
                request, HeaderName.contentType, ContentType.JSON
            )
            set_response_header(
                request, HeaderName.etag, hash(personnel)
            )
            return json_as_text([
                ranger_as_json(ranger)
                for ranger in personnel
            ])

        d = self.dms.personnel()
        d.addCallback(gotPersonnel)
        return d


    @app.route("/incident_types", methods=("GET",))
    @app.route("/incident_types/", methods=("GET",))
    @http_sauce
    def list_incident_types(self, request):
        set_response_header(
            request, HeaderName.contentType, ContentType.JSON
        )
        set_response_header(
            request, HeaderName.etag, hash(self.config.IncidentTypesJSON)
        )
        return self.config.IncidentTypesJSON


    @app.route("/incidents", methods=("GET",))
    @app.route("/incidents/", methods=("GET",))
    @http_sauce
    def list_incidents(self, request):
        #set_response_header(request, HeaderName.etag, "*") # FIXME
        set_response_header(request, HeaderName.contentType, ContentType.JSON)
        return json_as_text(sorted(
            incidents_from_query(self, request),
            cmp=lambda a, b: cmp(a[0], b[0]), reverse=True,
        ))


    @app.route("/incidents/<number>", methods=("GET",))
    @http_sauce
    def get_incident(self, request, number):
        # FIXME: For debugging
        #import time
        #time.sleep(0.3)

        number = int(number)

        set_response_header(
            request, HeaderName.etag,
            self.storage.etag_for_incident_with_number(number)
        )
        set_response_header(
            request, HeaderName.contentType, ContentType.JSON
        )

        if False:
            #
            # This is faster, but doesn't benefit from any cleanup or
            # validation code, so it's only OK if we know all data in the
            # store is clean by this server version's standards.
            #
            return self.storage.read_incident_with_number_raw(number)
        else:
            #
            # This parses the data from the store, validates it, then
            # re-serializes it.
            #
            incident = self.storage.read_incident_with_number(number)
            return json_as_text(incident_as_json(incident))


    @app.route("/incidents/<number>", methods=("POST",))
    @http_sauce
    def edit_incident(self, request, number):
        if self.config.ReadOnly:
            set_response_header(
                request, HeaderName.contentType, ContentType.plain
            )
            request.setResponseCode(http.FORBIDDEN)
            return "Server is in read-only mode."

        number = int(number)
        incident = self.storage.read_incident_with_number(number)

        #
        # Apply the changes requested by the client
        #
        edits_json = json_from_file(request.content)
        edits = incident_from_json(edits_json, number=number, validate=False)
        edit_incident(incident, edits, self.avatarId.decode("utf-8"))

        #
        # Write to disk
        #
        self.storage.write_incident(incident)

        #
        # Respond
        #
        set_response_header(request, HeaderName.contentType, ContentType.JSON)
        request.setResponseCode(http.OK)

        return ""


    @app.route("/incidents", methods=("POST",))
    @app.route("/incidents/", methods=("POST",))
    @http_sauce
    def new_incident(self, request):
        if self.config.ReadOnly:
            set_response_header(
                request, HeaderName.contentType, ContentType.plain
            )
            request.setResponseCode(http.FORBIDDEN)
            return "Server is in read-only mode."

        incident = Incident.from_json_io(
            request.content, number=self.storage.next_incident_number()
        )

        # Edit report entrys to add author
        for entry in incident.report_entries:
            entry.author = self.avatarId.decode("utf-8")

        self.storage.write_incident(incident)

        request.setResponseCode(http.CREATED)

        request.setHeader(
            HeaderName.incidentNumber.value,
            incident.number
        )
        request.setHeader(
            HeaderName.location.value,
            url_for(request, "get_incident", {"number": incident.number})
        )

        return ""


    # #
    # # Web UI
    # #

    @app.route("/queue", methods=("GET",))
    @app.route("/queue/", methods=("GET",))
    @http_sauce
    def dispatchQueue(self, request):
        if not request.args:
            request.args["show_closed"] = ["false"]

        set_response_header(
            request, HeaderName.contentType, ContentType.HTML
        )
        return DispatchQueueElement(self)


    @app.route("/queue/incidents/<number>", methods=("GET",))
    @http_sauce
    def queue_incident(self, request, number):
        set_response_header(
            request, HeaderName.contentType, ContentType.HTML
        )
        number = int(number)
        return IncidentElement(self, number)


    #
    # Static resources
    #

    @app.route("/resources", methods=("GET",))
    @app.route("/resources/", methods=("GET",), branch=True)
    @http_sauce
    def favicon(self, request):
        return File(self.config.Resources.path)


    # #
    # # Documentation
    # #

    @app.route("/", methods=("GET",))
    @http_sauce
    def root(self, request):
        set_response_header(
            request, HeaderName.contentType, ContentType.HTML
        )
        return HomePageElement(self)


    @app.route("/docs", methods=("GET",))
    @app.route("/docs/", methods=("GET",))
    @http_sauce
    def doc_index(self, request):
        return self.doc_with_name(request, "index.xhtml")


    @app.route("/docs/<name>", methods=("GET",))
    @http_sauce
    def doc_with_name(self, request, name):
        filePath = self.config.Resources.child("docs").child(name)

        if filePath.exists():
            if name.endswith(".xhtml"):
                set_response_header(
                    request, HeaderName.contentType, ContentType.HTML
                )
                return FileElement(filePath)

        request.setResponseCode(http.NOT_FOUND)
        set_response_header(
            request, HeaderName.contentType, ContentType.plain
        )
        return "Not found."


    # #
    # # Reports
    # #

    # @app.route("/reports/daily", methods=("GET",))
    # @http_sauce
    # def daily_report(self, request):
    #     set_response_header(
    #         request, HeaderName.contentType, ContentType.HTML
    #     )
    #     return DailyReportElement(self)


    # @app.route("/charts/daily", methods=("GET",))
    # @http_sauce
    # def daily_chart(self, request):
    #     set_response_header(
    #         request, HeaderName.contentType, ContentType.HTML
    #     )
    #     return DailyReportElement(self, template_name="chart_daily")


    # @app.route("/reports/shift", methods=("GET",))
    # @http_sauce
    # def shift_report(self, request):
    #     set_response_header(
    #         request, HeaderName.contentType, ContentType.HTML
    #     )
    #     return ShiftReportElement(self)


    #
    # Links
    #

    @app.route("/links", methods=("GET",))
    @app.route("/links/", methods=("GET",))
    @http_sauce
    def links(self, request):
        #set_response_header(request, HeaderName.etag, ????)
        set_response_header(request, HeaderName.contentType, ContentType.JSON)
        return json_as_text([
            {JSON.name.value: name, JSON.url.value: value}
            for name, value in (
                ("Home page", "/"),
                ("Dispatch Queue", "/queue"),
                ("Daily Incident Summary (Table)", "/reports/daily"),
                ("Daily Incident Summary (Chart)", "/charts/daily"),
            )
        ])


    #
    # Baseline
    #

    @app.route("/baseline/<container>/<name>", methods=("GET",))
    @http_sauce
    def baseline(self, request, container, name):
        # See http://baselinecss.com/
        return self.cachedZipResource(
            request=request,
            name="baseline",
            url="http://baselinecss.com/download/baseline.zip",
            segments=("baseline.0.5.3", "css", container, name)
        )


    #
    # JQuery resources
    #

    # @app.route("/jquery.js", methods=("GET",))
    # @http_sauce
    # def jquery(self, request):
    #     version = "jquery-1.10.2.min.js"
    #     url = "http://code.jquery.com/" + version
    #     return self.cachedResource(version, url)


    # @app.route("/jquery-1.10.2.min.map", methods=("GET",))
    # @http_sauce
    # def jquery_map(self, request):
    #     name = "jquery-1.10.2.min.map"
    #     url = "http://code.jquery.com/" + name
    #     return self.cachedResource(name, url)


    # _tidy_base_url = "https://raw.github.com/nuxy/Tidy-Table/v1.4/"

    # @app.route("/tidy.js", methods=("GET",))
    # @http_sauce
    # def tidy(self, request):
    #     name = "tidy.js"
    #     url = self._tidy_base_url + "jquery.tidy.table.min.js"
    #     return self.cachedResource(name, url)


    # @app.route("/tidy.css", methods=("GET",))
    # @http_sauce
    # def tidy_css(self, request):
    #     name = "tidy.css"
    #     url = self._tidy_base_url + "jquery.tidy.table.min.css"
    #     return self.cachedResource(name, url)


    # @app.route("/images/arrow_asc.gif", methods=("GET",))
    # @http_sauce
    # def tidy_asc(self, request):
    #     name = "tidy-asc.gif"
    #     url = self._tidy_base_url + "images/arrow_asc.gif"
    #     return self.cachedResource(name, url)


    # @app.route("/images/arrow_desc.gif", methods=("GET",))
    # @http_sauce
    # def tidy_desc(self, request):
    #     name = "tidy-desc.gif"
    #     url = self._tidy_base_url + "images/arrow_desc.gif"
    #     return self.cachedResource(name, url)


    #
    # Flot
    #

    # @app.route("/flot/<name>", methods=("GET",))
    # @http_sauce
    # def flot(self, request, name):
    #     # See http://www.flotcharts.org/
    #     which = "flot-0.8.1"
    #     return self.cachedZipResource(
    #         request=request,
    #         name=which,
    #         url="http://www.flotcharts.org/downloads/{0}.zip".format(which),
    #         segments=("flot", name)
    #     )


    #
    # Utilities
    #

    def cachedResource(self, name, url):
        name = "_{0}".format(name)
        filePath = self.config.CachedResources.child(name)

        if filePath.exists():
            return File(filePath.path)

        d = http_download(filePath, url)
        d.addCallback(lambda _: File(filePath.path))
        return d


    def cachedZipResource(self, request, name, url, segments):
        archivePath = self.config.CachedResources.child("{0}.zip".format(name))

        if archivePath.exists():
            d = Deferred()
            d.callback(None)
        else:
            d = http_download(archivePath, url)

        def readFromArchive(_):
            filePath = ZipArchive(archivePath.path)
            for segment in segments:
                filePath = filePath.child(segment)
            return filePath.getContent()

        def notFoundHandler(f):
            f.trap(KeyError)
            request.setResponseCode(http.NOT_FOUND)
            set_response_header(
                request, HeaderName.contentType, ContentType.plain
            )
            return "Not found."

        d.addCallback(readFromArchive)
        d.addErrback(notFoundHandler)
        return d
