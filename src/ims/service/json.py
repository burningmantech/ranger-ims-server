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

from twisted.internet.defer import Deferred, inlineCallbacks, returnValue
from twisted.internet.error import ConnectionDone

from util.tz import utcNow

from .auth import Authorization
from .error import NotAuthorizedError
from .http import ContentType, HeaderName, staticResource
from .klein import route
from .urls import URLs
from ..data.json import (
    JSON, incidentAsJSON, incidentFromJSON, incidentReportAsJSON,
    incidentReportFromJSON, jsonTextFromObject, objectFromJSONBytesIO,
    rangerAsJSON,
)
from ..data.model import Event, IncidentState, InvalidDataError, ReportEntry
from ..dms import DMSError


__all__ = (
    "JSONMixIn",
)



class JSONMixIn(object):
    """
    Mix-in for JSON API endpoints.
    """

    #
    # JSON API endpoints
    #

    @route(URLs.ping.asText(), methods=("HEAD", "GET"))
    @staticResource
    def pingResource(self, request):
        """
        Ping (health check) endpoint.
        """
        ack = b'"ack"'
        return self.jsonBytes(request, ack, bytes(hash(ack)))


    @route(URLs.personnel.asText(), methods=("HEAD", "GET"))
    @inlineCallbacks
    def personnelResource(self, request):
        """
        Personnel endpoint.
        """
        yield self.authorizeRequest(
            request, None, Authorization.readPersonnel
        )

        stream, etag = yield self.personnelData()
        returnValue(self.jsonStream(request, stream, etag))


    @inlineCallbacks
    def personnelData(self):
        """
        Data for personnel endpoint.
        """
        try:
            personnel = yield self.dms.personnel()
        except DMSError as e:
            self.log.error("Unable to vend personnel: {failure}", failure=e)
            personnel = ()

        returnValue((
            self.buildJSONArray(
                jsonTextFromObject(rangerAsJSON(ranger)).encode("utf-8")
                for ranger in personnel
            ),
            bytes(hash(personnel)),
        ))


    @route(URLs.incidentTypes.asText(), methods=("HEAD", "GET"))
    def incidentTypesResource(self, request):
        """
        Incident types endpoint.
        """
        self.authenticateRequest(request)

        hidden = self.queryValue(request, "hidden") == "true"

        incidentTypes = tuple(
            self.storage.allIncidentTypes(includeHidden=hidden)
        )

        stream = self.buildJSONArray(
            jsonTextFromObject(incidentType).encode("utf-8")
            for incidentType in incidentTypes
        )

        return self.jsonStream(request, stream, None)


    @route(URLs.incidentTypes.asText(), methods=("POST",))
    @inlineCallbacks
    def editIncidentTypesResource(self, request):
        """
        Incident types editing endpoint.
        """
        yield self.authorizeRequest(
            request, None, Authorization.imsAdmin
        )

        json = objectFromJSONBytesIO(request.content)

        if type(json) is not dict:
            returnValue(self.badRequestResource(
                request, "root: expected a dictionary.")
            )

        adds = json.get("add", [])
        show = json.get("show", [])
        hide = json.get("hide", [])

        if adds:
            if type(adds) is not list:
                returnValue(self.badRequestResource(
                    request, "add: expected a list.")
                )
            for incidentType in adds:
                self.storage.createIncidentType(incidentType)

        if show:
            if type(show) is not list:
                returnValue(self.badRequestResource(
                    request, "show: expected a list.")
                )
            self.storage.showIncidentTypes(show)

        if hide:
            if type(hide) is not list:
                returnValue(self.badRequestResource(
                    request, "hide: expected a list.")
                )
            self.storage.hideIncidentTypes(hide)

        returnValue(self.noContentResource(request))


    @route(URLs.locations.asText(), methods=("HEAD", "GET"))
    @inlineCallbacks
    def locationsResource(self, request, eventID):
        """
        Location list endpoint.
        """
        event = Event(eventID)

        yield self.authorizeRequest(
            request, event, Authorization.readIncidents
        )

        data = self.config.locationsJSONBytes
        returnValue(self.jsonBytes(request, data, bytes(hash(data))))


    @route(URLs.incidents.asText(), methods=("HEAD", "GET"))
    @inlineCallbacks
    def listIncidentsResource(self, request, eventID):
        """
        Incident list endpoint.
        """
        event = Event(eventID)

        yield self.authorizeRequest(
            request, event, Authorization.readIncidents
        )

        stream = self.buildJSONArray(
            jsonTextFromObject(incidentAsJSON(incident)).encode("utf-8")
            for incident in self.storage.incidents(event)
        )

        returnValue(self.jsonStream(request, stream, None))


    @route(URLs.incidents.asText(), methods=("POST",))
    @inlineCallbacks
    def newIncidentResource(self, request, eventID):
        """
        New incident endpoint.
        """
        event = Event(eventID)

        yield self.authorizeRequest(
            request, event, Authorization.writeIncidents
        )

        json = objectFromJSONBytesIO(request.content)
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
                request,
                "Created time {} is in the future. Current time is {}."
                .format(incident.created, now)
            ))

        self.storage.createIncident(event, incident, author)

        assert incident.number is not None

        self.log.info(
            "User {author} created new incident #{incident.number} via JSON",
            author=author, incident=incident
        )
        self.log.debug("New incident: {json}", json=incidentAsJSON(incident))

        request.setHeader(HeaderName.incidentNumber.value, incident.number)
        request.setHeader(
            HeaderName.location.value,
            "{}/{}".format(URLs.incidentNumber.asText(), incident.number)
        )
        returnValue(self.noContentResource(request))


    @route(URLs.incidentNumber.asText(), methods=("HEAD", "GET"))
    @inlineCallbacks
    def readIncidentResource(self, request, eventID, number):
        """
        Incident endpoint.
        """
        event = Event(eventID)

        yield self.authorizeRequest(
            request, event, Authorization.readIncidents
        )

        try:
            number = int(number)
        except ValueError:
            returnValue(self.notFoundResource(request))

        incident = self.storage.incident(event, number)
        text = jsonTextFromObject(incidentAsJSON(incident))

        returnValue(
            self.jsonBytes(request, text.encode("utf-8"), incident.version)
        )


    @route(URLs.incidentNumber.asText(), methods=("POST",))
    @inlineCallbacks
    def editIncidentResource(self, request, eventID, number):
        """
        Incident edit endpoint.
        """
        event = Event(eventID)

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
        edits = objectFromJSONBytesIO(request.content)

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
                def cast(obj):
                    return obj
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
    @inlineCallbacks
    def listIncidentReportsResource(self, request):
        """
        Incident reports endpoint.
        """
        eventID        = self.queryValue(request, "event")
        incidentNumber = self.queryValue(request, "incident")

        if eventID is None and incidentNumber is None:
            attachedTo = None
        elif eventID == incidentNumber == "":
            yield self.authorizeRequest(
                request, None, Authorization.readIncidentReports
            )
            attachedTo = (None, None)
        else:
            event = Event(eventID)
            try:
                event.validate()
            except InvalidDataError:
                returnValue(
                    self.invalidQueryResource(request, "event", eventID)
                )
            try:
                incidentNumber = int(incidentNumber)
            except ValueError:
                returnValue(
                    self.invalidQueryResource(
                        request, "incident", incidentNumber
                    )
                )
            yield self.authorizeRequest(
                request, event, Authorization.readIncidents
            )
            attachedTo = (event, incidentNumber)

        stream = self.buildJSONArray(
            jsonTextFromObject(
                incidentReportAsJSON(incidentReport)
            ).encode("utf-8")
            for incidentReport
            in self.storage.incidentReports(attachedTo=attachedTo)
        )

        returnValue(self.jsonStream(request, stream, None))


    @route(URLs.incidentReports.asText(), methods=("POST",))
    @inlineCallbacks
    def newIncidentReportResource(self, request):
        """
        New incident report endpoint.
        """
        yield self.authorizeRequest(
            request, None, Authorization.writeIncidentReports
        )

        json = objectFromJSONBytesIO(request.content)
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
                request,
                "Created time {} is in the future. Current time is {}."
                .format(incidentReport.created, now)
            ))

        self.storage.createIncidentReport(incidentReport)

        assert incidentReport.number is not None

        self.log.info(
            "User {author} created new incident report "
            "#{incidentReport.number} via JSON",
            author=author, incidentReport=incidentReport
        )
        self.log.debug(
            "New incident report: {json}",
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
        """
        Incident report endpoint.
        """
        try:
            number = int(number)
        except ValueError:
            returnValue(self.notFoundResource(request))

        yield self.authorizeRequestForIncidentReport(request, number)

        incidentReport = self.storage.incidentReport(number)
        text = jsonTextFromObject(incidentReportAsJSON(incidentReport))

        returnValue(
            self.jsonBytes(
                request, text.encode("utf-8"), incidentReport.version()
            )
        )


    @route(URLs.incidentReport.asText(), methods=("POST",))
    @inlineCallbacks
    def editIncidentReportResource(self, request, number):
        """
        Incident report edit endpoint.
        """
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
        action = self.queryValue(request, "action")

        if action is not None:
            eventID        = self.queryValue(request, "event")
            incidentNumber = self.queryValue(request, "incident")

            event = Event(eventID)
            try:
                event.validate()
            except InvalidDataError:
                returnValue(
                    self.invalidQueryResource(request, "event", eventID)
                )

            try:
                incidentNumber = int(incidentNumber)
            except ValueError:
                returnValue(self.invalidQueryResource(
                    request, "incident", incidentNumber
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
                returnValue(self.invalidQueryResource(
                    request, "action", action
                ))

        #
        # Get the edits requested by the client
        #
        edits = objectFromJSONBytesIO(request.content)

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
                def cast(obj):
                    return obj
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
        """
        Admin access control endpoint.
        """
        yield self.authorizeRequest(request, None, Authorization.imsAdmin)

        acl = {}
        for event in self.storage.events():
            acl[event.id] = dict(
                readers=self.storage.readers(event),
                writers=self.storage.writers(event),
            )
        returnValue(jsonTextFromObject(acl))


    @route(URLs.acl.asText(), methods=("POST",))
    @inlineCallbacks
    def editAdminAccessResource(self, request):
        """
        Admin access control edit endpoint.
        """
        yield self.authorizeRequest(request, None, Authorization.imsAdmin)

        edits = objectFromJSONBytesIO(request.content)

        for eventID, acl in edits.items():
            event = Event(eventID)
            if "readers" in acl:
                self.storage.setReaders(event, acl["readers"])
            if "writers" in acl:
                self.storage.setWriters(event, acl["writers"])

        returnValue(self.noContentResource(request))


    @route(URLs.streets.asText(), methods=("HEAD", "GET"))
    @inlineCallbacks
    def readStreetsResource(self, request):
        """
        Street list endpoint.
        """
        yield self.authorizeRequest(request, None, Authorization.imsAdmin)

        streets = {}
        for event in self.storage.events():
            streets[event.id] = self.storage.concentricStreetsByID(event)
        returnValue(jsonTextFromObject(streets))


    @route(URLs.streets.asText(), methods=("POST",))
    @inlineCallbacks
    def editStreetsResource(self, request):
        """
        Street list edit endpoint.
        """
        yield self.authorizeRequest(request, None, Authorization.imsAdmin)

        edits = objectFromJSONBytesIO(request.content)

        for eventID, _streets in edits.items():
            event = Event(eventID)
            existing = self.storage.concentricStreetsByID(event)

            for _streetID, _streetName in existing.items():
                raise NotAuthorizedError("Removal of streets is not allowed.")

        for eventID, streets in edits.items():
            event = Event(eventID)
            existing = self.storage.concentricStreetsByID(event)

            for streetID, streetName in streets.items():
                if streetID not in existing:
                    self.storage.createConcentricStreet(
                        event, streetID, streetName
                    )

        returnValue(self.noContentResource(request))


    @route(URLs.eventSource.asText(), methods=("GET",))
    def eventSourceResource(self, request):
        """
        HTML5 EventSource endpoint.
        """
        d = Deferred()

        self.log.info("Event source connected: {id}", id=id(request))

        request.setHeader(
            HeaderName.contentType.value, ContentType.eventStream.value
        )

        self.storeObserver.addListener(request)

        def disconnected(f):
            f.trap(ConnectionDone)
            self.log.info("Event source disconnected: {id}", id=id(request))
            self.storeObserver.removeListener(request)

        def finished(_):
            self.storeObserver.removeListener(request)
            raise AssertionError("This was not expected")

        df = request.notifyFinish()
        df.addCallbacks(finished, disconnected)

        return d
