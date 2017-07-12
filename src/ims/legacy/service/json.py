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
from enum import Enum
from typing import Any, Awaitable, Callable, Mapping, Optional, Tuple

from twisted.internet.defer import Deferred
from twisted.internet.error import ConnectionDone
from twisted.python.constants import NamedConstant
from twisted.python.failure import Failure
from twisted.web.iweb import IRequest

from ims.ext.json import jsonTextFromObject, objectFromJSONBytesIO
from ims.ext.klein import ContentType, HeaderName, KleinRenderable, static
from ims.model import (
    Event, Incident, IncidentReport, IncidentState, ReportEntry
)
from ims.model.json import (
    IncidentJSONKey, IncidentReportJSONKey, LocationJSONKey,
    ReportEntryJSONKey, RodGarettAddressJSONKey,
    jsonObjectFromModelObject, modelObjectFromJSONObject
)
from ims.store import NoSuchIncidentError

from .auth import Authorization
from .error import NotAuthorizedError
from .klein import invalidQueryResponse, notFoundResponse, queryValue, router
from .urls import URLs
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

    @router.route(URLs.ping.asText(), methods=("HEAD", "GET"))
    @static
    def pingResource(self, request: IRequest) -> KleinRenderable:
        """
        Ping (health check) endpoint.
        """
        ack = b'"ack"'
        return self.jsonBytes(request, ack, str(hash(ack)))


    @router.route(URLs.personnel.asText(), methods=("HEAD", "GET"))
    async def personnelResource(self, request: IRequest) -> KleinRenderable:
        """
        Personnel endpoint.
        """
        await self.auth.authorizeRequest(
            request, None, Authorization.readPersonnel
        )

        stream, etag = await self.personnelData()
        return self.jsonStream(request, stream, etag)


    async def personnelData(self) -> Tuple[bytes, str]:
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
                jsonTextFromObject(
                    jsonObjectFromModelObject(ranger)
                ).encode("utf-8")
                for ranger in personnel
            ),
            str(hash(personnel)),
        )


    @router.route(URLs.incidentTypes.asText(), methods=("HEAD", "GET"))
    async def incidentTypesResource(
        self, request: IRequest
    ) -> KleinRenderable:
        """
        Incident types endpoint.
        """
        self.auth.authenticateRequest(request)

        hidden = queryValue(request, "hidden") == "true"

        incidentTypes = tuple(
            await self.storage.incidentTypes(includeHidden=hidden)
        )

        stream = self.buildJSONArray(
            jsonTextFromObject(incidentType).encode("utf-8")
            for incidentType in incidentTypes
        )

        return self.jsonStream(request, stream, None)


    @router.route(URLs.incidentTypes.asText(), methods=("POST",))
    async def editIncidentTypesResource(
        self, request: IRequest
    ) -> KleinRenderable:
        """
        Incident types editing endpoint.
        """
        await self.auth.authorizeRequest(
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
                await self.storage.createIncidentType(incidentType)

        if show:
            if type(show) is not list:
                return self.badRequestResource(
                    request, "show: expected a list."
                )
            await self.storage.showIncidentTypes(show)

        if hide:
            if type(hide) is not list:
                return self.badRequestResource(
                    request, "hide: expected a list."
                )
            await self.storage.hideIncidentTypes(hide)

        return self.noContentResource(request)


    @router.route(URLs.locations.asText(), methods=("HEAD", "GET"))
    async def locationsResource(
        self, request: IRequest, eventID: str
    ) -> KleinRenderable:
        """
        Location list endpoint.
        """
        event = Event(eventID)

        await self.auth.authorizeRequest(
            request, event, Authorization.readIncidents
        )

        data = self.config.locationsJSONBytes
        return self.jsonBytes(request, data, str(hash(data)))


    @router.route(URLs.incidents.asText(), methods=("HEAD", "GET"))
    async def listIncidentsResource(
        self, request: IRequest, eventID: str
    ) -> KleinRenderable:
        """
        Incident list endpoint.
        """
        event = Event(eventID)

        await self.auth.authorizeRequest(
            request, event, Authorization.readIncidents
        )

        stream = self.buildJSONArray(
            jsonTextFromObject(
                jsonObjectFromModelObject(incident)
            ).encode("utf-8")
            for incident in await self.storage.incidents(event)
        )

        return self.jsonStream(request, stream, None)


    @router.route(URLs.incidents.asText(), methods=("POST",))
    async def newIncidentResource(
        self, request: IRequest, eventID: str
    ) -> KleinRenderable:
        """
        New incident endpoint.
        """
        event = Event(eventID)

        await self.auth.authorizeRequest(
            request, event, Authorization.writeIncidents
        )

        json = objectFromJSONBytesIO(request.content)
        incident = modelObjectFromJSONObject(json, Incident)

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

        await self.storage.createIncident(event, incident, author)

        assert incident.number is not None

        self.log.info(
            "User {author} created new incident #{incident.number} via JSON",
            author=author, incident=incident
        )
        self.log.debug(
            "New incident: {json}", json=jsonObjectFromModelObject(incident)
        )

        request.setHeader("Incident-Number", incident.number)
        request.setHeader(
            HeaderName.location.value,
            "{}/{}".format(URLs.incidentNumber.asText(), incident.number)
        )
        return self.noContentResource(request)


    @router.route(URLs.incidentNumber.asText(), methods=("HEAD", "GET"))
    async def readIncidentResource(
        self, request: IRequest, eventID: str, number: int
    ) -> KleinRenderable:
        """
        Incident endpoint.
        """
        event = Event(eventID)

        await self.auth.authorizeRequest(
            request, event, Authorization.readIncidents
        )

        try:
            number = int(number)
        except ValueError:
            return notFoundResponse(request)

        try:
            incident = await self.storage.incidentWithNumber(event, number)
        except NoSuchIncidentError:
            return notFoundResponse(request)

        data = (
            jsonTextFromObject(jsonObjectFromModelObject(incident))
            .encode("utf-8")
        )

        return self.jsonBytes(request, data)


    @router.route(URLs.incidentNumber.asText(), methods=("POST",))
    async def editIncidentResource(
        self, request: IRequest, eventID: str, number: int
    ) -> KleinRenderable:
        """
        Incident edit endpoint.
        """
        event = Event(eventID)

        await self.auth.authorizeRequest(
            request, event, Authorization.writeIncidents
        )

        author = request.user.shortNames[0]

        try:
            number = int(number)
        except ValueError:
            return notFoundResponse(request)

        #
        # Get the edits requested by the client
        #
        edits = objectFromJSONBytesIO(request.content)

        if not isinstance(edits, dict):
            return self.badRequestResource(
                request, "JSON incident must be a dictionary"
            )

        if edits.get(IncidentJSONKey.number.value, number) != number:
            return self.badRequestResource(
                request, "Incident number may not be modified"
            )

        UNSET = object()

        created = edits.get(IncidentJSONKey.created.value, UNSET)
        if created is not UNSET:
            return self.badRequestResource(
                request, "Incident created time may not be modified"
            )

        async def applyEdit(
            json: Mapping[str, Any], key: Enum,
            setter: Callable[[Event, int, Any, str], Awaitable[None]],
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
                await setter(event, number, _cast(value), author)

        storage = self.storage

        await applyEdit(
            edits, IncidentJSONKey.priority, storage.setIncidentPriority
        )

        await applyEdit(
            edits, IncidentJSONKey.state,
            storage.setIncidentState, lambda n: IncidentState[n]
        )

        await applyEdit(
            edits, IncidentJSONKey.summary, storage.setIncidentSummary
        )

        location = edits.get(IncidentJSONKey.location.value, UNSET)
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
                await applyEdit(
                    location, LocationJSONKey.name,
                    storage.setIncidentLocationName
                )
                await applyEdit(
                    location, RodGarettAddressJSONKey.concentric,
                    storage.setIncidentLocationConcentricStreet
                )
                await applyEdit(
                    location, RodGarettAddressJSONKey.radialHour,
                    storage.setIncidentLocationRadialHour
                )
                await applyEdit(
                    location, RodGarettAddressJSONKey.radialMinute,
                    storage.setIncidentLocationRadialMinute
                )
                await applyEdit(
                    location, RodGarettAddressJSONKey.description,
                    storage.setIncidentLocationDescription
                )

        await applyEdit(
            edits, IncidentJSONKey.rangerHandles, storage.setIncidentRangers
        )

        await applyEdit(
            edits, IncidentJSONKey.incidentTypes, storage.setIncidentTypes
        )

        entries = edits.get(IncidentJSONKey.reportEntries.value, UNSET)
        if entries is not UNSET:
            now = DateTime.now(TimeZone.utc)

            for entry in entries:
                text = entry.get(ReportEntryJSONKey.text.value, None)
                if text:
                    await storage.addIncidentReportEntry(
                        event, number,
                        ReportEntry(
                            author=author,
                            text=text,
                            created=now,
                            system_entry=False,
                        )
                    )

        return self.noContentResource(request)


    @router.route(URLs.incidentReports.asText(), methods=("HEAD", "GET"))
    async def listIncidentReportsResource(
        self, request: IRequest
    ) -> KleinRenderable:
        """
        Incident reports endpoint.
        """
        storage = self.storage

        eventID = queryValue(request, "event")
        incidentNumberText = queryValue(request, "incident")

        if eventID is None:
            return invalidQueryResponse(request, "event")

        if incidentNumberText is None:
            return invalidQueryResponse(request, "incident")

        if eventID == incidentNumberText == "":
            await self.auth.authorizeRequest(
                request, None, Authorization.readIncidentReports
            )
            incidentReports = await storage.detachedIncidentReports()

        else:
            try:
                event = Event(id=eventID)
            except ValueError:
                return invalidQueryResponse(
                    request, "event", eventID
                )

            try:
                incidentNumber = int(incidentNumberText)
            except ValueError:
                return invalidQueryResponse(
                    request, "incident", incidentNumberText
                )

            await self.auth.authorizeRequest(
                request, event, Authorization.readIncidents
            )
            incidentReports = await storage.incidentReportsAttachedToIncident(
                event=event, incidentNumber=incidentNumber
            )

        stream = self.buildJSONArray(
            jsonTextFromObject(
                jsonObjectFromModelObject(incidentReport)
            ).encode("utf-8")
            for incidentReport in incidentReports
        )

        return self.jsonStream(request, stream, None)


    @router.route(URLs.incidentReports.asText(), methods=("POST",))
    async def newIncidentReportResource(
        self, request: IRequest
    ) -> KleinRenderable:
        """
        New incident report endpoint.
        """
        await self.auth.authorizeRequest(
            request, None, Authorization.writeIncidentReports
        )

        json = objectFromJSONBytesIO(request.content)
        incidentReport = modelObjectFromJSONObject(json, IncidentReport)

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

        await self.storage.createIncidentReport(incidentReport)

        assert incidentReport.number is not None

        self.log.info(
            "User {author} created new incident report "
            "#{incidentReport.number} via JSON",
            author=author, incidentReport=incidentReport
        )
        self.log.debug(
            "New incident report: {json}",
            json=jsonObjectFromModelObject(incidentReport),
        )

        request.setHeader("Incident-Report-Number", incidentReport.number)
        request.setHeader(
            HeaderName.location.value,
            "{}/{}".format(URLs.incidentNumber.asText(), incidentReport.number)
        )
        return self.noContentResource(request)


    @router.route(URLs.incidentReport.asText(), methods=("HEAD", "GET"))
    async def readIncidentReportResource(
        self, request: IRequest, number: int
    ) -> KleinRenderable:
        """
        Incident report endpoint.
        """
        try:
            number = int(number)
        except ValueError:
            self.auth.authenticateRequest(request)
            return notFoundResponse(request)

        await self.auth.authorizeRequestForIncidentReport(request, number)

        incidentReport = await self.storage.incidentReport(number)
        text = jsonTextFromObject(jsonObjectFromModelObject(incidentReport))

        return self.jsonBytes(request, text.encode("utf-8"))


    @router.route(URLs.incidentReport.asText(), methods=("POST",))
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
            return notFoundResponse(request)

        #
        # Attach to incident if requested
        #
        action = queryValue(request, "action")

        if action is not None:
            eventID            = queryValue(request, "event")
            incidentNumberText = queryValue(request, "incident")

            if eventID is None:
                return invalidQueryResponse(request, "event")

            if incidentNumberText is None:
                return invalidQueryResponse(request, "incident")

            try:
                event = Event(id=eventID)
            except ValueError:
                return invalidQueryResponse(request, "event", eventID)

            try:
                incidentNumber = int(incidentNumberText)
            except ValueError:
                return invalidQueryResponse(
                    request, "incident", incidentNumberText
                )

            if action == "attach":
                await self.storage.attachIncidentReportToIncident(
                    number, event, incidentNumber
                )
            elif action == "detach":
                await self.storage.detachIncidentReportFromIncident(
                    number, event, incidentNumber
                )
            else:
                return invalidQueryResponse(request, "action", action)

        #
        # Get the edits requested by the client
        #
        edits = objectFromJSONBytesIO(request.content)

        if not isinstance(edits, dict):
            return self.badRequestResource(
                request, "JSON incident report must be a dictionary"
            )

        if edits.get(IncidentReportJSONKey.number.value, number) != number:
            return self.badRequestResource(
                request, "Incident report number may not be modified"
            )

        UNSET = object()

        created = edits.get(IncidentReportJSONKey.created.value, UNSET)
        if created is not UNSET:
            return self.badRequestResource(
                request, "Incident report created time may not be modified"
            )

        async def applyEdit(
            json: Mapping[str, Any], key: NamedConstant,
            setter: Callable[[Event, int, Any, str], Awaitable[None]],
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
                await setter(event, number, _cast(value), author)

        storage = self.storage

        await applyEdit(
            edits, IncidentReportJSONKey.summary,
            storage.setIncidentReportSummary
        )

        entries = edits.get(IncidentJSONKey.reportEntries.value, UNSET)
        if entries is not UNSET:
            now = DateTime.now(TimeZone.utc)

            for entry in entries:
                text = entry.get(ReportEntryJSONKey.text.value, None)
                if text:
                    await self.storage.addIncidentReportReportEntry(
                        number,
                        ReportEntry(
                            author=author,
                            text=text,
                            created=now,
                            system_entry=False,
                        )
                    )

        return self.noContentResource(request)


    @router.route(URLs.acl.asText(), methods=("HEAD", "GET"))
    async def readAdminAccessResource(
        self, request: IRequest
    ) -> KleinRenderable:
        """
        Admin access control endpoint.
        """
        await self.authorizeRequest(request, None, Authorization.imsAdmin)

        acl = {}
        for event in await self.storage.events():
            acl[event.id] = dict(
                readers=await self.storage.readers(event),
                writers=await self.storage.writers(event),
            )
        return jsonTextFromObject(acl)


    @router.route(URLs.acl.asText(), methods=("POST",))
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
                await self.storage.setReaders(event, acl["readers"])
            if "writers" in acl:
                await self.storage.setWriters(event, acl["writers"])

        return self.noContentResource(request)


    @router.route(URLs.streets.asText(), methods=("HEAD", "GET"))
    async def readStreetsResource(self, request: IRequest) -> KleinRenderable:
        """
        Street list endpoint.
        """
        await self.authorizeRequest(request, None, Authorization.imsAdmin)

        streets = {}
        for event in await self.storage.events():
            streets[event.id] = await self.storage.concentricStreets(event)
        return jsonTextFromObject(streets)


    @router.route(URLs.streets.asText(), methods=("POST",))
    async def editStreetsResource(self, request: IRequest) -> KleinRenderable:
        """
        Street list edit endpoint.
        """
        await self.authorizeRequest(request, None, Authorization.imsAdmin)

        edits = objectFromJSONBytesIO(request.content)

        for eventID, _streets in edits.items():
            event = Event(eventID)
            existing = await self.storage.concentricStreets(event)

            for _streetID, _streetName in existing.items():
                raise NotAuthorizedError("Removal of streets is not allowed.")

        for eventID, streets in edits.items():
            event = Event(eventID)
            existing = await self.storage.concentricStreets(event)

            for streetID, streetName in streets.items():
                if streetID not in existing:
                    await self.storage.createConcentricStreet(
                        event, streetID, streetName
                    )

        return self.noContentResource(request)


    @router.route(URLs.eventSource.asText(), methods=("GET",))
    def eventSourceResource(self, request: IRequest) -> KleinRenderable:
        """
        HTML5 EventSource endpoint.
        """
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
            # We don't expect anything to fire the returned deferred, so
            # this should never happen.
            self.storeObserver.removeListener(request)
            raise AssertionError("This was not expected")

        # Handle disconnect
        request.notifyFinish().addCallbacks(finished, disconnected)

        # Return an unfired deferred, so the connection doesn't close on this
        # end...
        return Deferred()
