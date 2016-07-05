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
from ..data.json import JSON, textFromJSON, jsonFromFile
from ..data.json import rangerAsJSON, incidentAsJSON, incidentFromJSON
from .http import HeaderName, fixedETag
from .klein import route
from .urls import URLs
from .auth import Authorization
from .error import NotAuthorizedError



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
    def personnelResource(self, request, event):
        yield self.authorizeRequest(
            request, event, Authorization.readIncidents
        )

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

        now = utcNow()
        if incident.created is not None and incident.created > now:
            returnValue(self.badRequestResource(
                "Created time {} is in the future. Current time is {}."
                .format(incident.created, now)
            ))

        author = request.user.shortNames[0]

        self.storage.createIncident(event, incident)

        self.log.info(
            u"User {author} created new incident #{incident.number} via JSON",
            author=author, incident=incident
        )
        self.log.debug(u"New: {json}", json=incidentAsJSON(incident))

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

        # # For simulating slow connections
        # import time
        # time.sleep(0.3)

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
            author = request.user.shortNames[0]

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
