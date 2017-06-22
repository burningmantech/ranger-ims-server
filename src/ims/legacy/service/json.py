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

from datetime import datetime as DateTime, timezone as TimeZone
from typing import Any, Callable, Mapping, Optional, Tuple

from twisted.internet.defer import Deferred
from twisted.internet.error import ConnectionDone
from twisted.python.constants import NamedConstant
from twisted.python.failure import Failure
from twisted.web.iweb import IRequest

from ims.ext.klein import KleinRenderable

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
from ...dms import DMSError


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
    def pingResource(self, request: IRequest) -> KleinRenderable:
        """
        Ping (health check) endpoint.
        """
        ack = b'"ack"'
        return self.jsonBytes(request, ack, bytes(hash(ack)))


    @route(URLs.personnel.asText(), methods=("HEAD", "GET"))
    async def personnelResource(self, request: IRequest) -> KleinRenderable:
        """
        Personnel endpoint.
        """
        await self.authorizeRequest(
            request, None, Authorization.readPersonnel
        )

        stream, etag = await self.personnelData()
        return self.jsonStream(request, stream, etag)


    async def personnelData(self) -> Tuple[bytes, bytes]:
        """
        Data for personnel endpoint.
        """
        try:
            personnel = await self.dms.personnel()
        except DMSError as e:
            self.log.error("Unable to vend personnel: {failure}", failure=e)
            personnel = ()

        return (
            self.buildJSONArray(
                jsonTextFromObject(rangerAsJSON(ranger)).encode("utf-8")
                for ranger in personnel
            ),
            bytes(hash(personnel)),
        )


    @route(URLs.incidentTypes.asText(), methods=("HEAD", "GET"))
    def incidentTypesResource(self, request: IRequest) -> KleinRenderable:
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
    async def editIncidentTypesResource(
        self, request: IRequest
    ) -> KleinRenderable:
        """
        Incident types editing endpoint.
        """
        await self.authorizeRequest(
            request, None, Authorization.imsAdmin
        )

        json = objectFromJSONBytesIO(request.content)

        if type(json) is not dict:
            return self.badRequestResource(
                request, "root: expected a dictionary."
            )

        adds = json.get("add", [])
        show = json.get("show", [])
        hide = json.get("hide", [])

        if adds:
            if type(adds) is not list:
                return self.badRequestResource(
                    request, "add: expected a list."
                )
            for incidentType in adds:
                self.storage.createIncidentType(incidentType)

        if show:
            if type(show) is not list:
                return self.badRequestResource(
                    request, "show: expected a list."
                )
            self.storage.showIncidentTypes(show)

        if hide:
            if type(hide) is not list:
                return self.badRequestResource(
                    request, "hide: expected a list."
                )
            self.storage.hideIncidentTypes(hide)

        return self.noContentResource(request)


    @route(URLs.locations.asText(), methods=("HEAD", "GET"))
    async def locationsResource(
        self, request: IRequest, eventID: str
    ) -> KleinRenderable:
        """
        Location list endpoint.
        """
        event = Event(eventID)

        await self.authorizeRequest(
            request, event, Authorization.readIncidents
        )

        data = self.config.locationsJSONBytes
        return self.jsonBytes(request, data, bytes(hash(data)))


    @route(URLs.incidents.asText(), methods=("HEAD", "GET"))
    async def listIncidentsResource(
        self, request: IRequest, eventID: str
    ) -> KleinRenderable:
        """
        Incident list endpoint.
        """
        event = Event(eventID)

        await self.authorizeRequest(
            request, event, Authorization.readIncidents
        )

        stream = self.buildJSONArray(
            jsonTextFromObject(incidentAsJSON(incident)).encode("utf-8")
            for incident in self.storage.incidents(event)
        )

        return self.jsonStream(request, stream, None)


    @route(URLs.incidents.asText(), methods=("POST",))
    async def newIncidentResource(
        self, request: IRequest, eventID: str
    ) -> KleinRenderable:
        """
        New incident endpoint.
        """
        event = Event(eventID)

        await self.authorizeRequest(
            request, event, Authorization.writeIncidents
        )

        json = objectFromJSONBytesIO(request.content)
        incident = incidentFromJSON(json, number=None, validate=False)

        if incident.state is None:
            incident.state = IncidentState.new

        author = request.user.shortNames[0]
        now = DateTime.now(TimeZone.utc)

        if incident.created is None:
            # No created timestamp provided; add one.

            # Right now is a decent default, but if there's a report entry
            # that's older than now, that's a better pick.
            created = DateTime.now(TimeZone.utc)
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
            return self.badRequestResource(
                request,
                "Created time {} is in the future. Current time is {}."
                .format(incident.created, now)
            )

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
        return self.noContentResource(request)


    @route(URLs.incidentNumber.asText(), methods=("HEAD", "GET"))
    async def readIncidentResource(
        self, request: IRequest, eventID: str, number: int
    ) -> KleinRenderable:
        """
        Incident endpoint.
        """
        event = Event(eventID)

        await self.authorizeRequest(
            request, event, Authorization.readIncidents
        )

        try:
            number = int(number)
        except ValueError:
            return self.notFoundResource(request)

        incident = self.storage.incident(event, number)
        text = jsonTextFromObject(incidentAsJSON(incident))

        return (
            self.jsonBytes(request, text.encode("utf-8"), incident.version)
        )


    @route(URLs.incidentNumber.asText(), methods=("POST",))
    async def editIncidentResource(
        self, request: IRequest, eventID: str, number: int
    ) -> KleinRenderable:
        """
        Incident edit endpoint.
        """
        event = Event(eventID)

        await self.authorizeRequest(
            request, event, Authorization.writeIncidents
        )

        author = request.user.shortNames[0]

        try:
            number = int(number)
        except ValueError:
            return self.notFoundResource(request)

        #
        # Get the edits requested by the client
        #
        edits = objectFromJSONBytesIO(request.content)

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

        def applyEdit(
            json: Mapping[str, Any], key: NamedConstant,
            setter: Callable[[Event, int, Any, str], None],
            cast: Optional[Callable[[Any], Any]] = None
        ) -> None:
            _cast: Callable[[Any], Any]
            if cast is None:
                def _cast(obj: Any) -> Any:
                    return obj
            else:
                _cast = cast
            value = json.get(key.value, UNSET)
            if value is not UNSET:
                setter(event, number, _cast(value), author)

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
            now = DateTime.now(TimeZone.utc)

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


    @route(URLs.incidentReports.asText(), methods=("HEAD", "GET"))
    async def listIncidentReportsResource(
        self, request: IRequest
    ) -> KleinRenderable:
        """
        Incident reports endpoint.
        """
        eventID        = self.queryValue(request, "event")
        incidentNumber = self.queryValue(request, "incident")

        if eventID is None and incidentNumber is None:
            attachedTo = None
        elif eventID == incidentNumber == "":
            await self.authorizeRequest(
                request, None, Authorization.readIncidentReports
            )
            attachedTo = (None, None)
        else:
            event = Event(eventID)
            try:
                event.validate()
            except InvalidDataError:
                return self.invalidQueryResource(
                    request, "event", eventID
                )
            try:
                incidentNumber = int(incidentNumber)
            except ValueError:
                return self.invalidQueryResource(
                    request, "incident", incidentNumber
                )
            await self.authorizeRequest(
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

        return self.jsonStream(request, stream, None)


    @route(URLs.incidentReports.asText(), methods=("POST",))
    async def newIncidentReportResource(
        self, request: IRequest
    ) -> KleinRenderable:
        """
        New incident report endpoint.
        """
        await self.authorizeRequest(
            request, None, Authorization.writeIncidentReports
        )

        json = objectFromJSONBytesIO(request.content)
        incidentReport = incidentReportFromJSON(
            json, number=None, validate=False
        )

        author = request.user.shortNames[0]
        now = DateTime.now(TimeZone.utc)

        if incidentReport.created is None:
            # No created timestamp provided; add one.

            # Right now is a decent default, but if there's a report entry
            # that's older than now, that's a better pick.
            created = DateTime.now(TimeZone.utc)
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
            return self.badRequestResource(
                request,
                "Created time {} is in the future. Current time is {}."
                .format(incidentReport.created, now)
            )

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
        return self.noContentResource(request)


    @route(URLs.incidentReport.asText(), methods=("HEAD", "GET"))
    async def readIncidentReportResource(
        self, request: IRequest, number: int
    ) -> KleinRenderable:
        """
        Incident report endpoint.
        """
        try:
            number = int(number)
        except ValueError:
            return self.notFoundResource(request)

        await self.authorizeRequestForIncidentReport(request, number)

        incidentReport = self.storage.incidentReport(number)
        text = jsonTextFromObject(incidentReportAsJSON(incidentReport))

        return self.jsonBytes(
            request, text.encode("utf-8"), incidentReport.version()
        )


    @route(URLs.incidentReport.asText(), methods=("POST",))
    async def editIncidentReportResource(
        self, request: IRequest, number: int
    ) -> KleinRenderable:
        """
        Incident report edit endpoint.
        """
        await self.authorizeRequest(
            request, None, Authorization.writeIncidentReports
        )

        author = request.user.shortNames[0]

        try:
            number = int(number)
        except ValueError:
            return self.notFoundResource(request)

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
                return self.invalidQueryResource(request, "event", eventID)

            try:
                incidentNumber = int(incidentNumber)
            except ValueError:
                return self.invalidQueryResource(
                    request, "incident", incidentNumber
                )

            if action == "attach":
                self.storage.attachIncidentReportToIncident(
                    number, event, incidentNumber
                )
            elif action == "detach":
                self.storage.detachIncidentReportFromIncident(
                    number, event, incidentNumber
                )
            else:
                return self.invalidQueryResource(request, "action", action)

        #
        # Get the edits requested by the client
        #
        edits = objectFromJSONBytesIO(request.content)

        if not isinstance(edits, dict):
            return self.badRequestResource(
                request, "JSON incident report must be a dictionary"
            )

        if edits.get(JSON.incident_report_number.value, number) != number:
            return self.badRequestResource(
                request, "Incident report number may not be modified"
            )

        UNSET = object()

        created = edits.get(JSON.incident_report_created.value, UNSET)
        if created is not UNSET:
            return self.badRequestResource(
                request, "Incident report created time may not be modified"
            )

        def applyEdit(
            json: Mapping[str, Any], key: NamedConstant,
            setter: Callable[[Event, int, Any, str], None],
            cast: Optional[Callable[[Any], Any]] = None
        ) -> None:
            _cast: Callable[[Any], Any]
            if cast is None:
                def _cast(obj: Any) -> Any:
                    return obj
            else:
                _cast = cast
            value = json.get(key.value, UNSET)
            if value is not UNSET:
                setter(event, number, _cast(value), author)

        storage = self.storage

        applyEdit(
            edits, JSON.incident_report_summary,
            storage.setIncidentReportSummary
        )

        entries = edits.get(JSON.report_entries.value, UNSET)
        if entries is not UNSET:
            now = DateTime.now(TimeZone.utc)

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

        return self.noContentResource(request)


    @route(URLs.acl.asText(), methods=("HEAD", "GET"))
    async def readAdminAccessResource(
        self, request: IRequest
    ) -> KleinRenderable:
        """
        Admin access control endpoint.
        """
        await self.authorizeRequest(request, None, Authorization.imsAdmin)

        acl = {}
        for event in self.storage.events():
            acl[event.id] = dict(
                readers=self.storage.readers(event),
                writers=self.storage.writers(event),
            )
        return jsonTextFromObject(acl)


    @route(URLs.acl.asText(), methods=("POST",))
    async def editAdminAccessResource(
        self, request: IRequest
    ) -> KleinRenderable:
        """
        Admin access control edit endpoint.
        """
        await self.authorizeRequest(request, None, Authorization.imsAdmin)

        edits = objectFromJSONBytesIO(request.content)

        for eventID, acl in edits.items():
            event = Event(eventID)
            if "readers" in acl:
                self.storage.setReaders(event, acl["readers"])
            if "writers" in acl:
                self.storage.setWriters(event, acl["writers"])

        return self.noContentResource(request)


    @route(URLs.streets.asText(), methods=("HEAD", "GET"))
    async def readStreetsResource(self, request: IRequest) -> KleinRenderable:
        """
        Street list endpoint.
        """
        await self.authorizeRequest(request, None, Authorization.imsAdmin)

        streets = {}
        for event in self.storage.events():
            streets[event.id] = self.storage.concentricStreetsByID(event)
        return jsonTextFromObject(streets)


    @route(URLs.streets.asText(), methods=("POST",))
    async def editStreetsResource(self, request: IRequest) -> KleinRenderable:
        """
        Street list edit endpoint.
        """
        await self.authorizeRequest(request, None, Authorization.imsAdmin)

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

        return self.noContentResource(request)


    @route(URLs.eventSource.asText(), methods=("GET",))
    def eventSourceResource(self, request: IRequest) -> KleinRenderable:
        """
        HTML5 EventSource endpoint.
        """
        d = Deferred()

        self.log.info("Event source connected: {id}", id=id(request))

        request.setHeader(
            HeaderName.contentType.value, ContentType.eventStream.value
        )

        self.storeObserver.addListener(request)

        def disconnected(f: Failure) -> None:
            f.trap(ConnectionDone)
            self.log.info("Event source disconnected: {id}", id=id(request))
            self.storeObserver.removeListener(request)

        def finished(_: Any) -> None:
            self.storeObserver.removeListener(request)
            raise AssertionError("This was not expected")

        df = request.notifyFinish()
        df.addCallbacks(finished, disconnected)

        return d
