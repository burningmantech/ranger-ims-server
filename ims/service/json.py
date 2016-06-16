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

from datetime import datetime as DateTime

from twisted.internet.defer import inlineCallbacks, returnValue

from ..tz import utcNow
from ..data.model import IncidentState, Incident, ReportEntry
from ..data.json import JSON, textFromJSON, jsonFromFile
from ..data.json import rangerAsJSON, incidentAsJSON, incidentFromJSON
from .http import HeaderName, fixedETag
from .klein import route
from .urls import URLs
from .auth import Authorization



class JSONMixIn(object):
    """
    Mix-in for JSON API endpoints.
    """

    #
    # JSON API endpoints
    #

    @route(URLs.pingURL.asText(), methods=("HEAD", "GET"))
    @route(URLs.pingURL.asText() + u"/", methods=("HEAD", "GET"))
    @fixedETag
    def pingResource(self, request, event):
        self.authenticateRequest(request)

        ack = b'"ack"'
        return self.jsonBytes(request, ack, bytes(hash(ack)))


    @route(URLs.personnelURL.asText(), methods=("HEAD", "GET"))
    @route(URLs.personnelURL.asText() + u"/", methods=("HEAD", "GET"))
    @inlineCallbacks
    def personnelResource(self, request, event):
        self.authorizeRequest(request, event, Authorization.readIncidents)

        stream, etag = yield self.personnelData()
        returnValue(self.jsonStream(request, stream, etag))


    @inlineCallbacks
    def personnelData(self):
        personnel = yield self.dms.personnel()
        returnValue((
            self.buildJSONArray(
                textFromJSON(rangerAsJSON(ranger)).encode("utf-8")
                for ranger in personnel
            ),
            bytes(hash(personnel)),
        ))


    @route(URLs.incidentTypesURL.asText(), methods=("HEAD", "GET"))
    @route(URLs.incidentTypesURL.asText() + u"/", methods=("HEAD", "GET"))
    def incidentTypesResource(self, request, event):
        self.authorizeRequest(request, event, Authorization.readIncidents)

        data = self.config.IncidentTypesJSONBytes
        return self.jsonBytes(request, data, bytes(hash(data)))


    @route(URLs.locationsURL.asText(), methods=("HEAD", "GET"))
    @route(URLs.locationsURL.asText() + u"/", methods=("HEAD", "GET"))
    def locationsResource(self, request, event):
        self.authorizeRequest(request, event, Authorization.readIncidents)

        data = self.config.locationsJSONBytes
        return self.jsonBytes(request, data, bytes(hash(data)))


    @route(URLs.incidentsURL.asText(), methods=("HEAD", "GET"))
    @route(URLs.incidentsURL.asText() + u"/", methods=("HEAD", "GET"))
    def listIncidentsResource(self, request, event):
        self.authorizeRequest(request, event, Authorization.readIncidents)

        incidents = self.storage[event].listIncidents()

        # Reverse order here because we generally want the clients to load the
        # more recent incidents first.
        # FIXME: Probably that should just be client-side logic.
        incidents = sorted(
            incidents, cmp=lambda a, b: cmp(a[0], b[0]), reverse=True
        )

        stream = self.buildJSONArray(
            textFromJSON(incident).encode("utf-8")
            for incident in incidents
        )

        return self.jsonStream(request, stream, None)


    @route(URLs.incidentsURL.asText(), methods=("POST",))
    @route(URLs.incidentsURL.asText() + u"/", methods=("POST",))
    def newIncidentResource(self, request, event):
        self.authorizeRequest(request, event, Authorization.writeIncidents)

        json = jsonFromFile(request.content)
        incident = incidentFromJSON(json, number=None, validate=False)

        now = utcNow()
        if incident.created is not None and incident.created > now:
            return self.badRequestResource(
                "Created time {} is in the future. Current time is {}."
                .format(incident.created, now)
            )

        author = request.user.uid

        number = self.storage.createIncident(event, incident)

        self.log.info(
            u"User {author} created new incident #{incident.number} via JSON",
            author=author, incident=incident
        )
        self.log.debug(u"New: {json}", json=incidentAsJSON(incident))

        request.setHeader(HeaderName.incidentNumber.value, number)
        request.setHeader(
            HeaderName.location.value,
            "{}/{}".format(URLs.incidentNumberURL.asText(), number)
        )
        return self.noContentResource(request)


    @route(URLs.incidentNumberURL.asText(), methods=("HEAD", "GET"))
    def readIncidentResource(self, request, event, number):
        self.authorizeRequest(request, event, Authorization.readIncidents)

        # # For simulating slow connections
        # import time
        # time.sleep(0.3)

        try:
            number = int(number)
        except ValueError:
            return self.notFoundResource(request)

        incident = self.storage.incident(event, number)
        text = textFromJSON(incidentAsJSON(incident))

        return self.jsonBytes(request, text.encode("utf-8"), incident.version)


    @route(URLs.incidentNumberURL.asText(), methods=("POST",))
    def editIncidentResource(self, request, event, number):
        self.authorizeRequest(request, event, Authorization.writeIncidents)

        try:
            number = int(number)
        except ValueError:
            return self.notFoundResource(request)

        #
        # Get the edits requested by the client
        #
        edits = jsonFromFile(request.content)

        if not isinstance(edits, dict):
            return self.badRequestResource(
                request, "JSON incident must be a dictionary"
            )

        if edits.get(JSON.incident_number.value, number) != number:
            return self.badRequestResource(
                request, "Incident number may not be modified"
            )

        UNSET = object()

        created = edits.get(JSON.incident_created.value, UNSET)
        if created is not UNSET:
            return self.badRequestResource(
                request, "Incident created time may not be modified"
            )

        def applyEdit(json, key, setter, cast=None):
            if cast is None:
                cast = lambda x: x
            value = json.get(key.value, UNSET)
            if value is not UNSET:
                setter(event, number, cast(value))

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
                storage.setIncidentLocationName(event, number, None)
                storage.setIncidentLocationConcentricStreet(event, number, None)
                storage.setIncidentLocationRadialHour(event, number, None)
                storage.setIncidentLocationRadialMinute(event, number, None)
                storage.setIncidentLocationDescription(event, number, None)
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
            author = request.user.uid

            now = DateTime.now()

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

        return self.noContentResource(request)
