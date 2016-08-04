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
Incident Management System JSON API endpoints.
"""

__all__ = [
    "JSONMixIn",
]

from twisted.internet.defer import inlineCallbacks, returnValue

from ..tz import utcNow
from ..data.model import IncidentState, ReportEntry
from ..data.json import (
    JSON, textFromJSON, jsonFromFile, rangerAsJSON,
    incidentAsJSON, incidentFromJSON,
    incidentReportAsJSON, incidentReportFromJSON,
)
from .http import HeaderName, fixedETag
from .klein import route
from .urls import URLs
from .auth import Authorization
from .error import NotAuthorizedError
from ..dms import DMSError



class JSONMixIn(object):
    """
    Mix-in for JSON API endpoints.
    """

    #
    # JSON API endpoints
    #

    @route(URLs.ping.asText(), methods=("HEAD", "GET"))
    @route(URLs.ping.asText() + u"/", methods=("HEAD", "GET"))
    @fixedETag
    def pingResource(self, request):
        ack = b'"ack"'
        return self.jsonBytes(request, ack, bytes(hash(ack)))


    @route(URLs.personnel.asText(), methods=("HEAD", "GET"))
    @route(URLs.personnel.asText() + u"/", methods=("HEAD", "GET"))
    @inlineCallbacks
    def personnelResource(self, request):
        yield self.authorizeRequest(
            request, None, Authorization.readPersonnel
        )

        stream, etag = yield self.personnelData()
        returnValue(self.jsonStream(request, stream, etag))


    @inlineCallbacks
    def personnelData(self):
        try:
            personnel = yield self.dms.personnel()
        except DMSError as e:
            self.log.error("Unable to vend personnel: {failure}", failure=e)
            personnel = ()

        returnValue((
            self.buildJSONArray(
                textFromJSON(rangerAsJSON(ranger)).encode("utf-8")
                for ranger in personnel
            ),
            bytes(hash(personnel)),
        ))


    @route(URLs.incidentTypes.asText(), methods=("HEAD", "GET"))
    @route(URLs.incidentTypes.asText() + u"/", methods=("HEAD", "GET"))
    def incidentTypesResource(self, request):
        self.authenticateRequest(request)

        hidden = request.args.get("hidden", [""])[0] == "true"

        incidentTypes = tuple(
            self.storage.allIncidentTypes(includeHidden=hidden)
        )

        stream = self.buildJSONArray(
            textFromJSON(incidentType).encode("utf-8")
            for incidentType in incidentTypes
        )

        return self.jsonStream(request, stream, None)


    @route(URLs.incidentTypes.asText(), methods=("POST",))
    @route(URLs.incidentTypes.asText() + u"/", methods=("POST",))
    @inlineCallbacks
    def editIncidentTypesResource(self, request):
        yield self.authorizeRequest(
            request, None, Authorization.imsAdmin
        )

        json = jsonFromFile(request.content)

        if type(json) is not dict:
            returnValue(self.badRequestResource("root: expected a dictionary."))

        adds = json.get("add" , [])
        show = json.get("show", [])
        hide = json.get("hide", [])

        if adds:
            if type(adds) is not list:
                returnValue(self.badRequestResource("add: expected a list."))
            for incidentType in adds:
                self.storage.createIncidentType(incidentType)

        if show:
            if type(show) is not list:
                returnValue(self.badRequestResource("show: expected a list."))
            self.storage.showIncidentTypes(show)

        if hide:
            if type(hide) is not list:
                returnValue(self.badRequestResource("hide: expected a list."))
            self.storage.hideIncidentTypes(hide)

        returnValue(self.noContentResource(request))


    @route(URLs.locations.asText(), methods=("HEAD", "GET"))
    @route(URLs.locations.asText() + u"/", methods=("HEAD", "GET"))
    @inlineCallbacks
    def locationsResource(self, request, event):
        yield self.authorizeRequest(
            request, event, Authorization.readIncidents
        )

        data = self.config.locationsJSONBytes
        returnValue(self.jsonBytes(request, data, bytes(hash(data))))


    @route(URLs.incidents.asText(), methods=("HEAD", "GET"))
    @route(URLs.incidents.asText() + u"/", methods=("HEAD", "GET"))
    @inlineCallbacks
    def listIncidentsResource(self, request, event):
        yield self.authorizeRequest(
            request, event, Authorization.readIncidents
        )

        stream = self.buildJSONArray(
            textFromJSON(incidentAsJSON(incident)).encode("utf-8")
            for incident in self.storage.incidents(event)
        )

        returnValue(self.jsonStream(request, stream, None))


    @route(URLs.incidents.asText(), methods=("POST",))
    @route(URLs.incidents.asText() + u"/", methods=("POST",))
    @inlineCallbacks
    def newIncidentResource(self, request, event):
        yield self.authorizeRequest(
            request, event, Authorization.writeIncidents
        )

        json = jsonFromFile(request.content)
        incident = incidentFromJSON(json, number=None, validate=False)

        if incident.state is None:
            incident.state = IncidentState.new

        author = request.user.shortNames[0]
        now = utcNow()

        if incident.created is None:
            # No created timestamp provided; add one.

            # Right now is a decent default, but if there's a report entry
            # that's older than now, that's a better pick.
            created = utcNow()
            if incident.reportEntries is not None:
                for entry in incident.reportEntries:
                    if entry.author is None:
                        entry.author = author
                    if entry.created is None:
                        entry.created = now
                    elif entry.created < created:
                        created = entry.created

            incident.created = created

        elif incident.created > now:
            returnValue(self.badRequestResource(
                "Created time {} is in the future. Current time is {}."
                .format(incident.created, now)
            ))

        self.storage.createIncident(event, incident, author)

        assert incident.number is not None

        self.log.info(
            u"User {author} created new incident #{incident.number} via JSON",
            author=author, incident=incident
        )
        self.log.debug(u"New incident: {json}", json=incidentAsJSON(incident))

        request.setHeader(HeaderName.incidentNumber.value, incident.number)
        request.setHeader(
            HeaderName.location.value,
            "{}/{}".format(URLs.incidentNumber.asText(), incident.number)
        )
        returnValue(self.noContentResource(request))


    @route(URLs.incidentNumber.asText(), methods=("HEAD", "GET"))
    @inlineCallbacks
    def readIncidentResource(self, request, event, number):
        yield self.authorizeRequest(
            request, event, Authorization.readIncidents
        )

        try:
            number = int(number)
        except ValueError:
            returnValue(self.notFoundResource(request))

        incident = self.storage.incident(event, number)
        text = textFromJSON(incidentAsJSON(incident))

        returnValue(
            self.jsonBytes(request, text.encode("utf-8"), incident.version)
        )


    @route(URLs.incidentNumber.asText(), methods=("POST",))
    @inlineCallbacks
    def editIncidentResource(self, request, event, number):
        yield self.authorizeRequest(
            request, event, Authorization.writeIncidents
        )

        author = request.user.shortNames[0]

        try:
            number = int(number)
        except ValueError:
            returnValue(self.notFoundResource(request))

        #
        # Get the edits requested by the client
        #
        edits = jsonFromFile(request.content)

        if not isinstance(edits, dict):
            returnValue(self.badRequestResource(
                request, "JSON incident must be a dictionary"
            ))

        if edits.get(JSON.incident_number.value, number) != number:
            returnValue(self.badRequestResource(
                request, "Incident number may not be modified"
            ))

        UNSET = object()

        created = edits.get(JSON.incident_created.value, UNSET)
        if created is not UNSET:
            returnValue(self.badRequestResource(
                request, "Incident created time may not be modified"
            ))

        def applyEdit(json, key, setter, cast=None):
            if cast is None:
                cast = lambda x: x
            value = json.get(key.value, UNSET)
            if value is not UNSET:
                setter(event, number, cast(value), author)

        storage = self.storage

        applyEdit(edits, JSON.incident_priority, storage.setIncidentPriority)

        applyEdit(
            edits, JSON.incident_state,
            storage.setIncidentState, IncidentState.lookupByName
        )

        applyEdit(edits, JSON.incident_summary, storage.setIncidentSummary)

        location = edits.get(JSON.incident_location.value, UNSET)
        if location is not UNSET:
            if location is None:
                for setter in (
                    storage.setIncidentLocationName,
                    storage.setIncidentLocationConcentricStreet,
                    storage.setIncidentLocationRadialHour,
                    storage.setIncidentLocationRadialMinute,
                    storage.setIncidentLocationDescription,
                ):
                    setter(event, number, None, author)
            else:
                applyEdit(
                    location, JSON.location_name,
                    storage.setIncidentLocationName
                )
                applyEdit(
                    location, JSON.location_garett_concentric,
                    storage.setIncidentLocationConcentricStreet
                )
                applyEdit(
                    location, JSON.location_garett_radial_hour,
                    storage.setIncidentLocationRadialHour
                )
                applyEdit(
                    location, JSON.location_garett_radial_minute,
                    storage.setIncidentLocationRadialMinute
                )
                applyEdit(
                    location, JSON.location_garett_description,
                    storage.setIncidentLocationDescription
                )

        applyEdit(edits, JSON.ranger_handles, storage.setIncidentRangers)

        applyEdit(edits, JSON.incident_types, storage.setIncidentTypes)

        entries = edits.get(JSON.report_entries.value, UNSET)
        if entries is not UNSET:
            now = utcNow()

            for entry in entries:
                text = entry.get(JSON.entry_text.value, None)
                if text:
                    storage.addIncidentReportEntry(
                        event, number,
                        ReportEntry(
                            author=author,
                            text=text,
                            created=now,
                            system_entry=False,
                        )
                    )

        returnValue(self.noContentResource(request))


    @route(URLs.incidentReports.asText(), methods=("HEAD", "GET"))
    @route(URLs.incidentReports.asText() + u"/", methods=("HEAD", "GET"))
    @inlineCallbacks
    def listIncidentReportsResource(self, request):
        event          = request.args.get("event"   , [""])[0]
        incidentNumber = request.args.get("incident", [""])[0]

        if event == incidentNumber == "":
            yield self.authorizeRequest(
                request, None, Authorization.readIncidentReports
            )
            attachedTo = (None, None)
        else:
            yield self.authorizeRequest(
                request, event, Authorization.readIncidents
            )
            attachedTo = (event, incidentNumber)

        stream = self.buildJSONArray(
            textFromJSON(incidentReportAsJSON(incidentReport)).encode("utf-8")
            for incidentReport
            in self.storage.incidentReports(attachedTo=attachedTo)
        )

        returnValue(self.jsonStream(request, stream, None))


    @route(URLs.incidentReports.asText(), methods=("POST",))
    @route(URLs.incidentReports.asText() + u"/", methods=("POST",))
    @inlineCallbacks
    def newIncidentReportResource(self, request):
        yield self.authorizeRequest(
            request, None, Authorization.writeIncidentReports
        )

        json = jsonFromFile(request.content)
        incidentReport = incidentReportFromJSON(
            json, number=None, validate=False
        )

        author = request.user.shortNames[0]
        now = utcNow()

        if incidentReport.created is None:
            # No created timestamp provided; add one.

            # Right now is a decent default, but if there's a report entry
            # that's older than now, that's a better pick.
            created = utcNow()
            if incidentReport.reportEntries is not None:
                for entry in incidentReport.reportEntries:
                    if entry.author is None:
                        entry.author = author
                    if entry.created is None:
                        entry.created = now
                    elif entry.created < created:
                        created = entry.created

            incidentReport.created = created

        elif incidentReport.created > now:
            returnValue(self.badRequestResource(
                "Created time {} is in the future. Current time is {}."
                .format(incidentReport.created, now)
            ))

        self.storage.createIncidentReport(incidentReport)

        assert incidentReport.number is not None

        self.log.info(
            u"User {author} created new incident report "
            u"#{incidentReport.number} via JSON",
            author=author, incidentReport=incidentReport
        )
        self.log.debug(
            u"New incident report: {json}",
            json=incidentReportAsJSON(incidentReport),
        )

        request.setHeader(
            HeaderName.incidentReportNumber.value, incidentReport.number
        )
        request.setHeader(
            HeaderName.location.value,
            "{}/{}".format(URLs.incidentNumber.asText(), incidentReport.number)
        )
        returnValue(self.noContentResource(request))


    @route(URLs.incidentReport.asText(), methods=("HEAD", "GET"))
    @inlineCallbacks
    def readIncidentReportResource(self, request, number):
        try:
            number = int(number)
        except ValueError:
            returnValue(self.notFoundResource(request))

        yield self.authorizeRequestForIncidentReport(request, number)

        incidentReport = self.storage.incidentReport(number)
        text = textFromJSON(incidentReportAsJSON(incidentReport))

        returnValue(
            self.jsonBytes(
                request, text.encode("utf-8"), incidentReport.version()
            )
        )


    @route(URLs.incidentReport.asText(), methods=("POST",))
    @inlineCallbacks
    def editIncidentReportResource(self, request, number):
        yield self.authorizeRequest(
            request, None, Authorization.writeIncidentReports
        )

        author = request.user.shortNames[0]

        try:
            number = int(number)
        except ValueError:
            returnValue(self.notFoundResource(request))

        #
        # Attach to incident if requested
        #
        action         = request.args.get("action"  , [""])[0]
        event          = request.args.get("event"   , [""])[0]
        incidentNumber = request.args.get("incident", [""])[0]

        if action != "":
            if event == "":
                returnValue(self.badRequestResource(
                    request, "No event specified: {}".format(action)
                ))
            if incidentNumber == "":
                returnValue(self.badRequestResource(
                    request, "No incident number specified: {}".format(action)
                ))

            try:
                incidentNumber = int(incidentNumber)
            except ValueError:
                returnValue(self.badRequestResource(
                    request,
                    "Invalid incident number: {!r}".format(incidentNumber)
                ))

            if action == "attach":
                self.storage.attachIncidentReportToIncident(
                    number, event, incidentNumber
                )
            elif action == "detach":
                self.storage.detachIncidentReportFromIncident(
                    number, event, incidentNumber
                )
            else:
                returnValue(self.badRequestResource(
                    request, "Unknown action: {}".format(action)
                ))

        #
        # Get the edits requested by the client
        #
        edits = jsonFromFile(request.content)

        if not isinstance(edits, dict):
            returnValue(self.badRequestResource(
                request, "JSON incident report must be a dictionary"
            ))

        if edits.get(JSON.incident_report_number.value, number) != number:
            returnValue(self.badRequestResource(
                request, "Incident report number may not be modified"
            ))

        UNSET = object()

        created = edits.get(JSON.incident_report_created.value, UNSET)
        if created is not UNSET:
            returnValue(self.badRequestResource(
                request, "Incident report created time may not be modified"
            ))

        def applyEdit(json, key, setter, cast=None):
            if cast is None:
                cast = lambda x: x
            value = json.get(key.value, UNSET)
            if value is not UNSET:
                setter(number, cast(value), author)

        storage = self.storage

        applyEdit(
            edits, JSON.incident_report_summary,
            storage.setIncidentReportSummary
        )

        entries = edits.get(JSON.report_entries.value, UNSET)
        if entries is not UNSET:
            now = utcNow()

            for entry in entries:
                text = entry.get(JSON.entry_text.value, None)
                if text:
                    self.storage.addIncidentReportReportEntry(
                        number,
                        ReportEntry(
                            author=author,
                            text=text,
                            created=now,
                            system_entry=False,
                        )
                    )

        returnValue(self.noContentResource(request))


    @route(URLs.acl.asText(), methods=("HEAD", "GET"))
    @inlineCallbacks
    def readAdminAccessResource(self, request):
        yield self.authorizeRequest(request, None, Authorization.imsAdmin)

        acl = {}
        for event in self.storage.events():
            acl[event] = dict(
                readers=self.storage.readers(event),
                writers=self.storage.writers(event),
            )
        returnValue(textFromJSON(acl))


    @route(URLs.acl.asText(), methods=("POST",))
    @inlineCallbacks
    def editAdminAccessResource(self, request):
        yield self.authorizeRequest(request, None, Authorization.imsAdmin)

        edits = jsonFromFile(request.content)

        for event, acl in edits.items():
            if "readers" in acl:
                self.storage.setReaders(event, acl["readers"])
            if "writers" in acl:
                self.storage.setWriters(event, acl["writers"])

        returnValue(self.noContentResource(request))


    @route(URLs.streets.asText(), methods=("HEAD", "GET"))
    @inlineCallbacks
    def readStreetsResource(self, request):
        yield self.authorizeRequest(request, None, Authorization.imsAdmin)

        streets = {}
        for event in self.storage.events():
            streets[event] = self.storage.concentricStreetsByID(event)
        returnValue(textFromJSON(streets))


    @route(URLs.streets.asText(), methods=("POST",))
    @inlineCallbacks
    def editStreetsResource(self, request):
        yield self.authorizeRequest(request, None, Authorization.imsAdmin)

        edits = jsonFromFile(request.content)

        for event, streets in edits.items():
            existing = self.storage.concentricStreetsByID(event)

            for streetID, streetName in existing.items():
                raise NotAuthorizedError("Removal of streets is not allowed.")

        for event, streets in edits.items():
            existing = self.storage.concentricStreetsByID(event)

            for streetID, streetName in streets.items():
                if streetID not in existing:
                    self.storage.createConcentricStreet(
                        event, streetID, streetName
                    )

        returnValue(self.noContentResource(request))
