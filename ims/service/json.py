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
from ..data.model import IncidentState, Incident, InvalidDataError
from ..data.json import textFromJSON, jsonFromFile
from ..data.json import rangerAsJSON, incidentAsJSON, incidentFromJSON
from ..data.edit import editIncident
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

        number = self.storage[event].nextIncidentNumber()

        json = jsonFromFile(request.content)
        incident = incidentFromJSON(json, number=number, validate=False)

        if incident.state is None:
            incident.state = IncidentState.new

        now = utcNow()

        if incident.created is None:
            # No timestamp provided; add one.

            # Right now is a decent default, but if there's a report entry
            # that's older than now, that's a better pick.
            created = now
            if incident.reportEntries is not None:
                for entry in incident.reportEntries:
                    if entry.created < created:
                        created = entry.created

            incident.created = created
            self.log.info(
                "Adding created time {created} to new incident #{number}",
                created=incident.created, number=number
            )
        else:
            if incident.created > now:
                return self.badRequestResource(
                    "Created time {} is in the future. Current time is {}."
                    .format(incident.created, now)
                )

        author = request.user.uid

        # Apply this new incident as changes to an empty incident so that
        # system report entries get added.
        # It also adds the author, so we don't need to do it here.
        incident = editIncident(
            Incident(
                number=incident.number,    # Must match
                created=incident.created,  # Must match
            ),
            incident,
            author
        )

        self.storage[event].writeIncident(incident)

        self.log.info(
            u"User {author} created new incident #{number} via JSON",
            author=author, number=number
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

        author = request.user.uid

        incident = self.storage.readIncidentWithNumber(event, number)

        #
        # Apply the changes requested by the client
        #
        jsonEdits = jsonFromFile(request.content)
        try:
            edits = incidentFromJSON(jsonEdits, number=number, validate=False)
        except InvalidDataError as e:
            return self.badRequestResource(request, e)
        edited = editIncident(incident, edits, author)

        #
        # Write to disk
        #
        storage.writeIncident(edited)

        self.log.debug(
            u"User {author} edited incident #{number} via JSON",
            author=author, number=number
        )
        # self.log.debug(u"Original: {json}", json=incidentAsJSON(incident))
        self.log.debug(u"Changes: {json}", json=jsonEdits)
        # self.log.debug(u"Edited: {json}", json=incidentAsJSON(edited))

        etag = storage.etagForIncidentWithNumber(number)

        return self.noContentResource(request, etag)
