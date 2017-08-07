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
from typing import (
    Any, Awaitable, Callable, Iterable, Mapping, Optional, Tuple, cast
)

from attr import attrib, attrs
from attr.validators import instance_of, provides

from hyperlink import URL

from twisted.internet.defer import Deferred
from twisted.internet.error import ConnectionDone
from twisted.logger import ILogObserver, Logger
from twisted.python.constants import NamedConstant
from twisted.python.failure import Failure
from twisted.web.iweb import IRequest

from ims.auth import AuthProvider, Authorization, NotAuthorizedError
from ims.config import Configuration, URLs
from ims.dms import DMSError
from ims.ext.json import jsonTextFromObject, objectFromJSONBytesIO
from ims.ext.klein import ContentType, HeaderName, KleinRenderable, static
from ims.model import (
    Event, Incident, IncidentPriority, IncidentReport, IncidentState,
    ReportEntry,
)
from ims.model.json import (
    IncidentJSONKey, IncidentReportJSONKey, LocationJSONKey,
    ReportEntryJSONKey, RodGarettAddressJSONKey,
    jsonObjectFromModelObject, modelObjectFromJSONObject
)
from ims.store import NoSuchIncidentError

from ._klein import (
    Router, badRequestResponse, invalidQueryResponse, noContentResponse,
    notFoundResponse, queryValue
)
from ._static import buildJSONArray, jsonBytes, writeJSONStream


__all__ = (
    "APIApplication",
)


def _unprefix(url: URL) -> URL:
    prefix = URLs.api.path[:-1]
    assert url.path[:len(prefix)] == prefix, (url.path[len(prefix):], prefix)
    return url.replace(path=url.path[len(prefix):])



@attrs(frozen=True)
class APIApplication(object):
    """
    Application with JSON API endpoints.
    """

    _log = Logger()
    router = Router()


    auth: AuthProvider = attrib(validator=instance_of(AuthProvider))
    config: Configuration = attrib(validator=instance_of(Configuration))
    storeObserver: ILogObserver = attrib(validator=provides(ILogObserver))


    @router.route(_unprefix(URLs.ping), methods=("HEAD", "GET"))
    @static
    def pingResource(self, request: IRequest) -> KleinRenderable:
        """
        Ping (health check) endpoint.
        """
        ack = b'"ack"'
        return jsonBytes(request, ack, str(hash(ack)))


    @router.route(_unprefix(URLs.personnel), methods=("HEAD", "GET"))
    async def personnelResource(self, request: IRequest) -> KleinRenderable:
        """
        Personnel endpoint.
        """
        await self.auth.authorizeRequest(
            request, None, Authorization.readPersonnel
        )

        stream, etag = await self.personnelData()
        writeJSONStream(request, stream, etag)
        return None


    async def personnelData(self) -> Tuple[Iterable[bytes], str]:
        """
        Data for personnel endpoint.
        """
        try:
            personnel = await self.config.dms.personnel()
        except DMSError as e:
            self._log.error("Unable to vend personnel: {failure}", failure=e)
            personnel = ()

        return (
            buildJSONArray(
                jsonTextFromObject(
                    jsonObjectFromModelObject(ranger)
                ).encode("utf-8")
                for ranger in personnel
            ),
            str(hash(personnel)),
        )


    @router.route(_unprefix(URLs.incidentTypes), methods=("HEAD", "GET"))
    async def incidentTypesResource(
        self, request: IRequest
    ) -> None:
        """
        Incident types endpoint.
        """
        self.auth.authenticateRequest(request)

        hidden = queryValue(request, "hidden") == "true"

        incidentTypes = tuple(
            await self.config.storage.incidentTypes(includeHidden=hidden)
        )

        stream = buildJSONArray(
            jsonTextFromObject(incidentType).encode("utf-8")
            for incidentType in incidentTypes
        )

        writeJSONStream(request, stream, None)


    @router.route(_unprefix(URLs.incidentTypes), methods=("POST",))
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
            return badRequestResponse(
                request, "root: expected a dictionary."
            )

        adds = json.get("add", [])
        show = json.get("show", [])
        hide = json.get("hide", [])

        storage = self.config.storage

        if adds:
            if type(adds) is not list:
                return badRequestResponse(
                    request, "add: expected a list."
                )
            for incidentType in adds:
                await storage.createIncidentType(incidentType)

        if show:
            if type(show) is not list:
                return badRequestResponse(
                    request, "show: expected a list."
                )
            await storage.showIncidentTypes(show)

        if hide:
            if type(hide) is not list:
                return badRequestResponse(
                    request, "hide: expected a list."
                )
            await storage.hideIncidentTypes(hide)

        return noContentResponse(request)


    @router.route(_unprefix(URLs.locations), methods=("HEAD", "GET"))
    async def locationsResource(
        self, request: IRequest, eventID: str
    ) -> KleinRenderable:
        """
        Location list endpoint.
        """
        event = Event(id=eventID)

        await self.auth.authorizeRequest(
            request, event, Authorization.readIncidents
        )

        data = self.config.locationsJSONBytes
        return jsonBytes(request, data, str(hash(data)))


    @router.route(_unprefix(URLs.incidents), methods=("HEAD", "GET"))
    async def listIncidentsResource(
        self, request: IRequest, eventID: str
    ) -> None:
        """
        Incident list endpoint.
        """
        event = Event(id=eventID)

        await self.auth.authorizeRequest(
            request, event, Authorization.readIncidents
        )

        stream = buildJSONArray(
            jsonTextFromObject(
                jsonObjectFromModelObject(incident)
            ).encode("utf-8")
            for incident in await self.config.storage.incidents(event)
        )

        writeJSONStream(request, stream, None)


    @router.route(_unprefix(URLs.incidents), methods=("POST",))
    async def newIncidentResource(
        self, request: IRequest, eventID: str
    ) -> KleinRenderable:
        """
        New incident endpoint.
        """
        event = Event(id=eventID)

        await self.auth.authorizeRequest(
            request, event, Authorization.writeIncidents
        )

        json = objectFromJSONBytesIO(request.content)
        incident = modelObjectFromJSONObject(json, Incident)

        if incident.event != event:
            return badRequestResponse(
                request,
                "Incident's event {} does not match event in URL {}"
                .format(incident.event, event)
            )

        if incident.state is None:
            incident.state = IncidentState.new

        author = request.user.shortNames[0]
        now = DateTime.now(TimeZone.utc)

        if incident.created is None:
            # No created timestamp provided; add one.

            # Right now is a decent default, but if there's a report entry
            # that's older than now, that's a better pick.
            created = now
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
            return badRequestResponse(
                request,
                "Created time {} is in the future. Current time is {}."
                .format(incident.created, now)
            )

        await self.config.storage.createIncident(incident, author)

        assert incident.number is not None

        self._log.info(
            "User {author} created new incident #{incident.number} via JSON",
            author=author, incident=incident
        )
        self._log.debug(
            "New incident: {json}", json=jsonObjectFromModelObject(incident)
        )

        request.setHeader("Incident-Number", incident.number)
        request.setHeader(
            HeaderName.location.value,
            "{}/{}".format(URLs.incidentNumber.asText(), incident.number)
        )
        return noContentResponse(request)


    @router.route(_unprefix(URLs.incidentNumber), methods=("HEAD", "GET"))
    async def readIncidentResource(
        self, request: IRequest, eventID: str, number: int
    ) -> KleinRenderable:
        """
        Incident endpoint.
        """
        event = Event(id=eventID)

        await self.auth.authorizeRequest(
            request, event, Authorization.readIncidents
        )

        try:
            number = int(number)
        except ValueError:
            return notFoundResponse(request)

        try:
            incident = await self.config.storage.incidentWithNumber(
                event, number
            )
        except NoSuchIncidentError:
            return notFoundResponse(request)

        data = (
            jsonTextFromObject(jsonObjectFromModelObject(incident))
            .encode("utf-8")
        )

        return jsonBytes(request, data)


    @router.route(_unprefix(URLs.incidentNumber), methods=("POST",))
    async def editIncidentResource(
        self, request: IRequest, eventID: str, number: int
    ) -> KleinRenderable:
        """
        Incident edit endpoint.
        """
        event = Event(id=eventID)

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
            return badRequestResponse(
                request, "JSON incident must be a dictionary"
            )

        if edits.get(IncidentJSONKey.number.value, number) != number:
            return badRequestResponse(
                request, "Incident number may not be modified"
            )

        UNSET = object()

        created = edits.get(IncidentJSONKey.created.value, UNSET)
        if created is not UNSET:
            return badRequestResponse(
                request, "Incident created time may not be modified"
            )

        IncidentAttributeSetter = (
            Callable[[Event, int, Any, str], Awaitable[None]]
        )

        async def applyEdit(
            json: Mapping[str, Any], key: Enum,
            setter: IncidentAttributeSetter,
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

        storage = self.config.storage

        await applyEdit(
            edits, IncidentJSONKey.priority, storage.setIncident_priority,
            lambda json: modelObjectFromJSONObject(json, IncidentPriority),
        )

        await applyEdit(
            edits, IncidentJSONKey.state,
            storage.setIncident_state,
            lambda json: modelObjectFromJSONObject(json, IncidentState),
        )

        await applyEdit(
            edits, IncidentJSONKey.summary, storage.setIncident_summary
        )

        location = edits.get(IncidentJSONKey.location.value, UNSET)
        if location is not UNSET:
            if location is None:
                for setter in (
                    storage.setIncident_locationName,
                    storage.setIncident_locationConcentricStreet,
                    storage.setIncident_locationRadialHour,
                    storage.setIncident_locationRadialMinute,
                    storage.setIncident_locationDescription,
                ):
                    cast(IncidentAttributeSetter, setter)(
                        event, number, None, author
                    )
            else:
                await applyEdit(
                    location, LocationJSONKey.name,
                    storage.setIncident_locationName
                )
                await applyEdit(
                    location, RodGarettAddressJSONKey.concentric,
                    storage.setIncident_locationConcentricStreet
                )
                await applyEdit(
                    location, RodGarettAddressJSONKey.radialHour,
                    storage.setIncident_locationRadialHour
                )
                await applyEdit(
                    location, RodGarettAddressJSONKey.radialMinute,
                    storage.setIncident_locationRadialMinute
                )
                await applyEdit(
                    location, RodGarettAddressJSONKey.description,
                    storage.setIncident_locationDescription
                )

        await applyEdit(
            edits, IncidentJSONKey.rangerHandles, storage.setIncident_rangers
        )

        await applyEdit(
            edits, IncidentJSONKey.incidentTypes,
            storage.setIncident_incidentTypes,
        )

        jsonEntries = edits.get(IncidentJSONKey.reportEntries.value, UNSET)
        if jsonEntries is not UNSET:
            now = DateTime.now(TimeZone.utc)

            entries = (
                ReportEntry(
                    author=author,
                    text=jsonEntry[ReportEntryJSONKey.text.value],
                    created=now,
                    automatic=False,
                )
                for jsonEntry in jsonEntries
            )

            await storage.addReportEntriesToIncident(
                event, number, entries, author
            )

        return noContentResponse(request)


    @router.route(_unprefix(URLs.incidentReports), methods=("HEAD", "GET"))
    async def listIncidentReportsResource(
        self, request: IRequest
    ) -> KleinRenderable:
        """
        Incident reports endpoint.
        """
        storage = self.config.storage

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

        stream = buildJSONArray(
            jsonTextFromObject(
                jsonObjectFromModelObject(incidentReport)
            ).encode("utf-8")
            for incidentReport in incidentReports
        )

        writeJSONStream(request, stream, None)
        return None


    @router.route(_unprefix(URLs.incidentReports), methods=("POST",))
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
            created = now
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
            return badRequestResponse(
                request,
                "Created time {} is in the future. Current time is {}."
                .format(incidentReport.created, now)
            )

        await self.config.storage.createIncidentReport(incidentReport, author)

        assert incidentReport.number is not None

        self._log.info(
            "User {author} created new incident report "
            "#{incidentReport.number} via JSON",
            author=author, incidentReport=incidentReport
        )
        self._log.debug(
            "New incident report: {json}",
            json=jsonObjectFromModelObject(incidentReport),
        )

        request.setHeader("Incident-Report-Number", incidentReport.number)
        request.setHeader(
            HeaderName.location.value,
            "{}/{}".format(URLs.incidentNumber.asText(), incidentReport.number)
        )
        return noContentResponse(request)


    @router.route(_unprefix(URLs.incidentReport), methods=("HEAD", "GET"))
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

        incidentReport = await self.config.storage.incidentReportWithNumber(
            number
        )
        text = jsonTextFromObject(jsonObjectFromModelObject(incidentReport))

        return jsonBytes(request, text.encode("utf-8"))


    @router.route(_unprefix(URLs.incidentReport), methods=("POST",))
    async def editIncidentReportResource(
        self, request: IRequest, number: int
    ) -> KleinRenderable:
        """
        Incident report edit endpoint.
        """
        await self.auth.authorizeRequest(
            request, None, Authorization.writeIncidentReports
        )

        author = request.user.shortNames[0]

        try:
            number = int(number)
        except ValueError:
            return notFoundResponse(request)

        storage = self.config.storage

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
                await storage.attachIncidentReportToIncident(
                    number, event, incidentNumber
                )
            elif action == "detach":
                await storage.detachIncidentReportFromIncident(
                    number, event, incidentNumber
                )
            else:
                return invalidQueryResponse(request, "action", action)

        #
        # Get the edits requested by the client
        #
        edits = objectFromJSONBytesIO(request.content)

        if not isinstance(edits, dict):
            return badRequestResponse(
                request, "JSON incident report must be a dictionary"
            )

        if edits.get(IncidentReportJSONKey.number.value, number) != number:
            return badRequestResponse(
                request, "Incident report number may not be modified"
            )

        UNSET = object()

        created = edits.get(IncidentReportJSONKey.created.value, UNSET)
        if created is not UNSET:
            return badRequestResponse(
                request, "Incident report created time may not be modified"
            )

        async def applyEdit(
            json: Mapping[str, Any], key: NamedConstant,
            setter: Callable[[int, Any, str], Awaitable[None]],
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
                await setter(number, _cast(value), author)

        await applyEdit(
            edits, IncidentReportJSONKey.summary,
            storage.setIncidentReport_summary
        )

        jsonEntries = edits.get(IncidentJSONKey.reportEntries.value, UNSET)
        if jsonEntries is not UNSET:
            now = DateTime.now(TimeZone.utc)

            entries = (
                ReportEntry(
                    author=author,
                    text=jsonEntry[ReportEntryJSONKey.text.value],
                    created=now,
                    automatic=False,
                )
                for jsonEntry in jsonEntries
            )

            await storage.addReportEntriesToIncidentReport(
                number, entries, author
            )

        return noContentResponse(request)


    @router.route(_unprefix(URLs.acl), methods=("HEAD", "GET"))
    async def readAdminAccessResource(
        self, request: IRequest
    ) -> KleinRenderable:
        """
        Admin access control endpoint.
        """
        await self.auth.authorizeRequest(request, None, Authorization.imsAdmin)

        storage = self.config.storage

        acl = {}
        for event in await storage.events():
            acl[event.id] = dict(
                readers=await storage.readers(event),
                writers=await storage.writers(event),
            )
        return jsonTextFromObject(acl)


    @router.route(_unprefix(URLs.acl), methods=("POST",))
    async def editAdminAccessResource(
        self, request: IRequest
    ) -> KleinRenderable:
        """
        Admin access control edit endpoint.
        """
        await self.auth.authorizeRequest(request, None, Authorization.imsAdmin)

        storage = self.config.storage

        edits = objectFromJSONBytesIO(request.content)

        for eventID, acl in edits.items():
            event = Event(id=eventID)
            if "readers" in acl:
                await storage.setReaders(event, acl["readers"])
            if "writers" in acl:
                await storage.setWriters(event, acl["writers"])

        return noContentResponse(request)


    @router.route(_unprefix(URLs.streets), methods=("HEAD", "GET"))
    async def readStreetsResource(self, request: IRequest) -> KleinRenderable:
        """
        Street list endpoint.
        """
        await self.auth.authorizeRequest(request, None, Authorization.imsAdmin)

        storage = self.config.storage

        streets = {}
        for event in await storage.events():
            streets[event.id] = await storage.concentricStreets(event)
        return jsonTextFromObject(streets)


    @router.route(_unprefix(URLs.streets), methods=("POST",))
    async def editStreetsResource(self, request: IRequest) -> KleinRenderable:
        """
        Street list edit endpoint.
        """
        await self.auth.authorizeRequest(request, None, Authorization.imsAdmin)

        storage = self.config.storage

        edits = objectFromJSONBytesIO(request.content)

        for eventID, _streets in edits.items():
            event = Event(id=eventID)
            existing = await storage.concentricStreets(event)

            for _streetID, _streetName in existing.items():
                raise NotAuthorizedError("Removal of streets is not allowed.")

        for eventID, streets in edits.items():
            event = Event(id=eventID)
            existing = await storage.concentricStreets(event)

            for streetID, streetName in streets.items():
                if streetID not in existing:
                    await storage.createConcentricStreet(
                        event, streetID, streetName
                    )

        return noContentResponse(request)


    @router.route(_unprefix(URLs.eventSource), methods=("GET",))
    def eventSourceResource(self, request: IRequest) -> KleinRenderable:
        """
        HTML5 EventSource endpoint.
        """
        self._log.debug("Event source connected: {id}", id=id(request))

        request.setHeader(
            HeaderName.contentType.value, ContentType.eventStream.value
        )

        self.storeObserver.addListener(request)

        def disconnected(f: Failure) -> None:
            f.trap(ConnectionDone)
            self._log.debug("Event source disconnected: {id}", id=id(request))
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
