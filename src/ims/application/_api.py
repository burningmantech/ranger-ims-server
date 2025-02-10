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

from collections.abc import (
    AsyncIterable,
    Awaitable,
    Callable,
    Iterable,
    Mapping,
)
from datetime import UTC
from datetime import datetime as DateTime
from enum import Enum
from functools import partial
from json import JSONDecodeError
from typing import Any, ClassVar, cast

from attrs import frozen
from hyperlink import URL
from klein import KleinRenderable
from klein._app import KleinSynchronousRenderable
from twisted.internet.defer import Deferred
from twisted.internet.error import ConnectionDone
from twisted.logger import Logger
from twisted.python.failure import Failure
from twisted.web import http
from twisted.web.iweb import IRequest

from ims.auth import Authorization, NotAuthorizedError
from ims.config import Configuration, URLs
from ims.directory import DirectoryError, IMSUser
from ims.ext.json_ext import (
    jsonTextFromObject,
    objectFromJSONBytesIO,
    objectFromJSONText,
)
from ims.ext.klein import ContentType, HeaderName, static
from ims.model import (
    AccessEntry,
    Event,
    FieldReport,
    Incident,
    IncidentPriority,
    IncidentState,
    ReportEntry,
)
from ims.model.jsons import (
    FieldReportJSONKey,
    IncidentJSONKey,
    IncidentPriorityJSONValue,
    IncidentStateJSONValue,
    JSONCodecError,
    LocationJSONKey,
    ReportEntryJSONKey,
    RodGarettAddressJSONKey,
    jsonObjectFromModelObject,
    modelObjectFromJSONObject,
)
from ims.store import NoSuchIncidentError

from ._eventsource import DataStoreEventSourceLogObserver
from ._klein import (
    Router,
    badGatewayResponse,
    badRequestResponse,
    invalidJSONResponse,
    invalidQueryResponse,
    noContentResponse,
    notFoundResponse,
    queryValue,
)
from ._static import buildJSONArray, jsonBytes, writeJSONStream


__all__ = ("APIApplication",)


def _unprefix(url: URL) -> URL:
    prefix = URLs.api.path[:-1]
    assert url.path[: len(prefix)] == prefix, (url.path[len(prefix) :], prefix)
    return url.replace(path=url.path[len(prefix) :])


def _urlToTextForBag(url: URL) -> str:
    return url.to_text().replace("<", "{").replace(">", "}")


@frozen(kw_only=True, eq=False)
class APIApplication:
    """
    Application with JSON API endpoints.
    """

    _log: ClassVar[Logger] = Logger()
    router: ClassVar[Router] = Router()

    _bag: ClassVar[bytes] = jsonTextFromObject(
        {
            "urls": {
                "ping": _urlToTextForBag(URLs.ping),
                "bag": _urlToTextForBag(URLs.bag),
                "auth": _urlToTextForBag(URLs.auth),
                "access": _urlToTextForBag(URLs.acl),
                "streets": _urlToTextForBag(URLs.streets),
                "personnel": _urlToTextForBag(URLs.personnel),
                "incident_types": _urlToTextForBag(URLs.incidentTypes),
                "events": _urlToTextForBag(URLs.events),
                "event": _urlToTextForBag(URLs.event),
                "incidents": _urlToTextForBag(URLs.incidents),
                "incident": _urlToTextForBag(URLs.incidentNumber),
                "field_reports": _urlToTextForBag(URLs.fieldReports),
                "field_report": _urlToTextForBag(URLs.fieldReport),
                "event_source": _urlToTextForBag(URLs.eventSource),
            },
        }
    ).encode("utf-8")

    config: Configuration
    storeObserver: DataStoreEventSourceLogObserver

    @router.route(_unprefix(URLs.ping), methods=("HEAD", "GET"))
    def pingResource(self, request: IRequest) -> KleinRenderable:
        """
        Ping (health check) endpoint.
        """
        ack = b'"ack"'
        return jsonBytes(request, ack, str(hash(ack)))

    @router.route(_unprefix(URLs.bag), methods=("HEAD", "GET"))
    @static
    def bagResource(self, request: IRequest) -> KleinRenderable:
        """
        Ping (health check) endpoint.
        """
        return jsonBytes(request, self._bag, str(hash(self._bag)))

    @router.route(_unprefix(URLs.auth), methods=("POST",))
    async def authResource(self, request: IRequest) -> KleinSynchronousRenderable:
        """
        Authentication endpoint.
        """
        contentType = request.getHeader(HeaderName.contentType.value)

        if contentType != ContentType.json.value:
            return badRequestResponse(
                request, f"Unsupported request Content-Type: {contentType}"
            )

        body = request.content.read()
        try:
            json = objectFromJSONText(body.decode("utf-8"))
        except JSONDecodeError as e:
            return invalidJSONResponse(request, e)

        username = json.get("identification")
        password = json.get("password")

        if username is None:
            return badRequestResponse(request, "Missing identification.")

        if password is None:
            return badRequestResponse(request, "Missing password.")

        try:
            user = await self.config.directory.lookupUser(username)
        except DirectoryError as e:
            self._log.error("Directory error: {error}", error=e)
            return badGatewayResponse(request, "Unable to contact directory service")

        if user is None:
            self._log.debug("Login failed: no such user: {username}", username=username)
        else:
            authProvider = self.config.authProvider
            authenticated = await authProvider.verifyPassword(user, password)
            if not authenticated:
                self._log.debug(
                    "Login failed: incorrect credentials for user: {user}",
                    user=user,
                )

            else:
                self._log.info("Issuing credentials for user {user}", user=user)
                credentials = await authProvider.credentialsForUser(
                    user, self.config.tokenLifetime
                )
                return jsonBytes(
                    request, jsonTextFromObject(credentials).encode("utf-8")
                )

        request.setResponseCode(http.UNAUTHORIZED)
        return jsonBytes(
            request,
            jsonTextFromObject({"status": "invalid-credentials"}).encode("utf-8"),
        )

    @router.route(_unprefix(URLs.personnel), methods=("HEAD", "GET"))
    @static
    async def personnelResource(self, request: IRequest) -> KleinSynchronousRenderable:
        """
        Personnel endpoint.
        """
        eventId = queryValue(request, "event_id")
        await self.config.authProvider.authorizeRequest(
            request, eventId, Authorization.readPersonnel
        )

        stream, etag = await self.personnelData()
        writeJSONStream(request, stream, etag)
        return None

    async def personnelData(self) -> tuple[Iterable[bytes], str]:
        """
        Data for personnel endpoint.
        """
        try:
            personnel = await self.config.directory.personnel()
        except DirectoryError as e:
            self._log.error("Unable to vend personnel: {failure}", failure=e)
            personnel = ()

        return (
            buildJSONArray(
                jsonTextFromObject(jsonObjectFromModelObject(ranger)).encode("utf-8")
                for ranger in personnel
            ),
            str(hash(personnel)),
        )

    @router.route(_unprefix(URLs.incidentTypes), methods=("HEAD", "GET"))
    @static
    async def incidentTypesResource(
        self, request: IRequest
    ) -> KleinSynchronousRenderable:
        """
        Incident types endpoint.
        """
        self.config.authProvider.authenticateRequest(request)

        hidden = queryValue(request, "hidden") == "true"

        incidentTypes = tuple(
            await self.config.store.incidentTypes(includeHidden=hidden)
        )

        stream = buildJSONArray(
            jsonTextFromObject(incidentType).encode("utf-8")
            for incidentType in incidentTypes
        )

        writeJSONStream(request, stream, None)
        return None

    @router.route(_unprefix(URLs.incidentTypes), methods=("POST",))
    async def editIncidentTypesResource(
        self, request: IRequest
    ) -> KleinSynchronousRenderable:
        """
        Incident types editing endpoint.
        """
        await self.config.authProvider.authorizeRequest(
            request, None, Authorization.imsAdmin
        )

        try:
            json = objectFromJSONBytesIO(request.content)
        except JSONDecodeError as e:
            return invalidJSONResponse(request, e)

        if type(json) is not dict:
            return badRequestResponse(request, "root: expected a dictionary.")

        adds = json.get("add", [])
        show = json.get("show", [])
        hide = json.get("hide", [])

        store = self.config.store

        if adds:
            if type(adds) is not list:
                return badRequestResponse(request, "add: expected a list.")
            for incidentType in adds:
                await store.createIncidentType(incidentType)

        if show:
            if type(show) is not list:
                return badRequestResponse(request, "show: expected a list.")
            await store.showIncidentTypes(show)

        if hide:
            if type(hide) is not list:
                return badRequestResponse(request, "hide: expected a list.")
            await store.hideIncidentTypes(hide)

        return noContentResponse(request)

    @router.route(_unprefix(URLs.events), methods=("HEAD", "GET"))
    async def eventsResource(self, request: IRequest) -> KleinSynchronousRenderable:
        """
        Events endpoint.
        """
        self.config.authProvider.authenticateRequest(request)

        authorizationsForUser = partial(
            self.config.authProvider.authorizationsForUser,
            getattr(request, "user", None),
        )

        jsonEvents = [
            jsonObjectFromModelObject(event)
            for event in await self.config.store.events()
            if Authorization.readIncidents & await authorizationsForUser(event.id)
        ]

        data = jsonTextFromObject(jsonEvents).encode("utf-8")

        return jsonBytes(request, data, str(hash(data)))

    @router.route(_unprefix(URLs.events), methods=("POST",))
    async def editEventsResource(self, request: IRequest) -> KleinSynchronousRenderable:
        """
        Events editing endpoint.
        """
        await self.config.authProvider.authorizeRequest(
            request, None, Authorization.imsAdmin
        )

        try:
            json = objectFromJSONBytesIO(request.content)
        except JSONDecodeError as e:
            return invalidJSONResponse(request, e)

        if type(json) is not dict:
            self._log.debug(
                "Events update expected a dictionary, got {json!r}", json=json
            )
            return badRequestResponse(request, "root: expected a dictionary.")

        adds = json.get("add", [])

        store = self.config.store

        if adds:
            if type(adds) is not list:
                self._log.debug(
                    "Events add expected a list, got {adds!r}",
                    json=json,
                    adds=adds,
                )
                return badRequestResponse(request, "add: expected a list.")
            for eventID in adds:
                await store.createEvent(Event(id=eventID))

        return noContentResponse(request)

    @router.route(_unprefix(URLs.incidents), methods=("HEAD", "GET"))
    async def listIncidentsResource(self, request: IRequest, event_id: str) -> None:
        """
        Incident list endpoint.
        """
        await self.config.authProvider.authorizeRequest(
            request, event_id, Authorization.readIncidents
        )

        excludeSystemEntries = queryValue(request, "exclude_system_entries") == "true"

        stream = buildJSONArray(
            jsonTextFromObject(jsonObjectFromModelObject(incident)).encode("utf-8")
            for incident in await self.config.store.incidents(
                event_id, excludeSystemEntries=excludeSystemEntries
            )
        )

        writeJSONStream(request, stream, None)

    @router.route(_unprefix(URLs.incidents), methods=("POST",))
    async def newIncidentResource(
        self, request: IRequest, event_id: str
    ) -> KleinSynchronousRenderable:
        """
        New incident endpoint.
        """
        await self.config.authProvider.authorizeRequest(
            request, event_id, Authorization.writeIncidents
        )

        try:
            json = objectFromJSONBytesIO(request.content)
        except JSONDecodeError as e:
            return invalidJSONResponse(request, e)

        user: IMSUser = request.user  # type: ignore[attr-defined]
        author = user.shortNames[0]
        now = DateTime.now(UTC)
        jsonNow = jsonObjectFromModelObject(now)

        # Set JSON incident number to 0
        # Set JSON incident created time to now

        for incidentKey in (
            IncidentJSONKey.number,
            IncidentJSONKey.created,
        ):
            if incidentKey.value in json:
                return badRequestResponse(
                    request, f"New incident may not specify {incidentKey.value}"
                )

        json[IncidentJSONKey.number.value] = 0
        json[IncidentJSONKey.created.value] = jsonNow

        # If not provided, set JSON event, state to new, priority to normal

        if IncidentJSONKey.eventID.value not in json:
            json[IncidentJSONKey.eventID.value] = event_id

        if IncidentJSONKey.state.value not in json:
            json[IncidentJSONKey.state.value] = IncidentStateJSONValue.new.value

        if IncidentJSONKey.priority.value not in json:
            json[IncidentJSONKey.priority.value] = (
                IncidentPriorityJSONValue.normal.value
            )

        # If not provided, set JSON handles, types, entries,
        # field report numbers to an empty list

        for incidentKey in (
            IncidentJSONKey.rangerHandles,
            IncidentJSONKey.incidentTypes,
            IncidentJSONKey.reportEntries,
            IncidentJSONKey.fieldReportNumbers,
        ):
            if incidentKey.value not in json:
                json[incidentKey.value] = []

        # Set JSON report entry created time to now
        # Set JSON report entry author
        # Set JSON report entry automatic=False

        for entryJSON in json[IncidentJSONKey.reportEntries.value]:
            for reportEntryKey in (
                ReportEntryJSONKey.created,
                ReportEntryJSONKey.author,
                ReportEntryJSONKey.automatic,
            ):
                if reportEntryKey.value in entryJSON:
                    return badRequestResponse(
                        request,
                        f"New report entry may not specify {reportEntryKey.value}",
                    )

            entryJSON[ReportEntryJSONKey.created.value] = jsonNow
            entryJSON[ReportEntryJSONKey.author.value] = author
            entryJSON[ReportEntryJSONKey.automatic.value] = False

        # Deserialize JSON incident

        try:
            incident = modelObjectFromJSONObject(json, Incident)
        except JSONCodecError as e:
            return badRequestResponse(request, str(e))

        # Validate data

        if incident.eventID != event_id:
            return badRequestResponse(
                request,
                f"Incident's event ID {incident.eventID} does not match event "
                f"ID in URL {event_id}",
            )

        # Store the incident

        incident = await self.config.store.createIncident(incident, author)

        self._log.info(
            "User {author} created new incident #{incident.number} via JSON",
            author=author,
            incident=incident,
        )
        self._log.debug(
            "New incident: {json}", json=jsonObjectFromModelObject(incident)
        )

        request.setHeader("X-IMS-Incident-Number", str(incident.number))
        request.setHeader(
            HeaderName.location.value,
            URLs.incidents.child(str(incident.number)).asText(),
        )
        return noContentResponse(request)

    @router.route(_unprefix(URLs.incidentNumber), methods=("HEAD", "GET"))
    async def readIncidentResource(
        self, request: IRequest, event_id: str, incident_number: str
    ) -> KleinSynchronousRenderable:
        """
        Incident endpoint.
        """
        await self.config.authProvider.authorizeRequest(
            request, event_id, Authorization.readIncidents
        )

        try:
            incidentNumber = int(incident_number)
        except ValueError:
            return notFoundResponse(request)
        del incident_number

        try:
            incident = await self.config.store.incidentWithNumber(
                event_id, incidentNumber
            )
        except NoSuchIncidentError:
            return notFoundResponse(request)

        data = jsonTextFromObject(jsonObjectFromModelObject(incident)).encode("utf-8")

        return jsonBytes(request, data)

    @router.route(_unprefix(URLs.incidentNumber), methods=("POST",))
    async def editIncidentResource(
        self, request: IRequest, event_id: str, incident_number: str
    ) -> KleinSynchronousRenderable:
        """
        Incident edit endpoint.
        """
        await self.config.authProvider.authorizeRequest(
            request, event_id, Authorization.writeIncidents
        )

        user: IMSUser = request.user  # type: ignore[attr-defined]
        author = user.shortNames[0]

        try:
            incidentNumber = int(incident_number)
        except ValueError:
            return notFoundResponse(request)
        del incident_number

        #
        # Get the edits requested by the client
        #
        try:
            edits = objectFromJSONBytesIO(request.content)
        except JSONDecodeError as e:
            return invalidJSONResponse(request, e)

        if not isinstance(edits, dict):
            return badRequestResponse(request, "JSON incident must be a dictionary")

        if edits.get(IncidentJSONKey.number.value, incidentNumber) != incidentNumber:
            return badRequestResponse(request, "Incident number may not be modified")

        UNSET = object()

        created = edits.get(IncidentJSONKey.created.value, UNSET)
        if created is not UNSET:
            return badRequestResponse(
                request, "Incident created time may not be modified"
            )

        IncidentAttributeSetter = Callable[[str, int, Any, str], Awaitable[None]]

        async def applyEdit(
            json: Mapping[str, Any],
            key: Enum,
            setter: IncidentAttributeSetter,
            cast: Callable[[Any], Any] | None = None,
        ) -> None:
            _cast: Callable[[Any], Any]
            if cast is None:

                def _cast(obj: Any) -> Any:
                    return obj

            else:
                _cast = cast
            value = json.get(key.value, UNSET)
            if value is not UNSET:
                await setter(event_id, incidentNumber, _cast(value), author)

        store = self.config.store

        try:
            await applyEdit(
                edits,
                IncidentJSONKey.priority,
                store.setIncident_priority,
                lambda json: modelObjectFromJSONObject(json, IncidentPriority),
            )
            await applyEdit(
                edits,
                IncidentJSONKey.state,
                store.setIncident_state,
                lambda json: modelObjectFromJSONObject(json, IncidentState),
            )
        except JSONCodecError as e:
            return badRequestResponse(request, str(e))

        await applyEdit(edits, IncidentJSONKey.summary, store.setIncident_summary)
        await applyEdit(edits, IncidentJSONKey.rangerHandles, store.setIncident_rangers)
        await applyEdit(
            edits,
            IncidentJSONKey.incidentTypes,
            store.setIncident_incidentTypes,
        )

        location = edits.get(IncidentJSONKey.location.value, UNSET)
        if location is not UNSET:
            if location is None:
                for setter in (
                    store.setIncident_locationName,
                    store.setIncident_locationConcentricStreet,
                    store.setIncident_locationRadialHour,
                    store.setIncident_locationRadialMinute,
                    store.setIncident_locationDescription,
                ):
                    cast(IncidentAttributeSetter, setter)(
                        event_id, incidentNumber, None, author
                    )
            else:
                await applyEdit(
                    location,
                    LocationJSONKey.name,
                    store.setIncident_locationName,
                )
                await applyEdit(
                    location,
                    RodGarettAddressJSONKey.concentric,
                    store.setIncident_locationConcentricStreet,
                )
                await applyEdit(
                    location,
                    RodGarettAddressJSONKey.radialHour,
                    store.setIncident_locationRadialHour,
                )
                await applyEdit(
                    location,
                    RodGarettAddressJSONKey.radialMinute,
                    store.setIncident_locationRadialMinute,
                )
                await applyEdit(
                    location,
                    RodGarettAddressJSONKey.description,
                    store.setIncident_locationDescription,
                )

        jsonEntries = edits.get(IncidentJSONKey.reportEntries.value, UNSET)
        if jsonEntries is not UNSET:
            now = DateTime.now(UTC)

            entries = (
                ReportEntry(
                    id=-1,  # will be assigned a valid ID on write to DB
                    author=author,
                    text=jsonEntry[ReportEntryJSONKey.text.value],
                    created=now,
                    automatic=False,
                    stricken=False,
                )
                for jsonEntry in jsonEntries
            )

            await store.addReportEntriesToIncident(
                event_id, incidentNumber, entries, author
            )

        return noContentResponse(request)

    @router.route(_unprefix(URLs.incident_reportEntry), methods=("POST",))
    async def editIncidentReportEntryResource(
        self,
        request: IRequest,
        event_id: str,
        incident_number: str,
        report_entry_id: str,
    ) -> KleinSynchronousRenderable:
        eventId = event_id
        incidentNumber = int(incident_number)
        reportEntryId = int(report_entry_id)
        del event_id
        del incident_number
        del report_entry_id
        await self.config.authProvider.authorizeRequest(
            request, eventId, Authorization.writeIncidents
        )

        store = self.config.store

        user: IMSUser = request.user  # type: ignore[attr-defined]
        author = user.shortNames[0]

        #
        # Get the edits requested by the client
        #
        try:
            edits = objectFromJSONBytesIO(request.content)
        except JSONDecodeError as e:
            return invalidJSONResponse(request, e)

        if not isinstance(edits, dict):
            return badRequestResponse(request, "JSON incident must be a dictionary")

        if ReportEntryJSONKey.stricken.value in edits:
            newVal = bool(edits.get(ReportEntryJSONKey.stricken.value))
            await store.setIncidentReportEntry_stricken(
                eventId, incidentNumber, reportEntryId, newVal, author
            )
        else:
            self._log.info("no key in request")

        return noContentResponse(request)

    @router.route(_unprefix(URLs.fieldReports), methods=("HEAD", "GET"))
    async def listFieldReportsResource(
        self, request: IRequest, event_id: str
    ) -> KleinSynchronousRenderable:
        """
        Field reports endpoint.
        """
        try:
            await self.config.authProvider.authorizeRequest(
                request, event_id, Authorization.readIncidents
            )
            limitedAccess = False
        except NotAuthorizedError:
            await self.config.authProvider.authorizeRequest(
                request, event_id, Authorization.writeFieldReports
            )
            limitedAccess = True

        incidentNumberText = queryValue(request, "incident")
        excludeSystemEntries = queryValue(request, "exclude_system_entries") == "true"

        store = self.config.store

        fieldReports: Iterable[FieldReport]
        if limitedAccess:
            user: IMSUser = request.user  # type: ignore[attr-defined]
            fieldReports = (
                fieldReport
                for fieldReport in await store.fieldReports(
                    event_id, excludeSystemEntries=excludeSystemEntries
                )
                if user.shortNames[0]
                in (entry.author for entry in fieldReport.reportEntries)
            )
        elif incidentNumberText is None:
            fieldReports = await store.fieldReports(
                event_id, excludeSystemEntries=excludeSystemEntries
            )
        else:
            try:
                incidentNumber = int(incidentNumberText)
            except ValueError:
                return invalidQueryResponse(request, "incident", incidentNumberText)

            fieldReports = await store.fieldReportsAttachedToIncident(
                eventID=event_id, incidentNumber=incidentNumber
            )

        stream = buildJSONArray(
            jsonTextFromObject(jsonObjectFromModelObject(fieldReport)).encode("utf-8")
            for fieldReport in fieldReports
        )

        writeJSONStream(request, stream, None)
        return None

    @router.route(_unprefix(URLs.fieldReports), methods=("POST",))
    async def newFieldReportResource(
        self, request: IRequest, event_id: str
    ) -> KleinSynchronousRenderable:
        """
        New field report endpoint.
        """
        await self.config.authProvider.authorizeRequest(
            request, event_id, Authorization.writeFieldReports
        )

        try:
            json = objectFromJSONBytesIO(request.content)
        except JSONDecodeError as e:
            return invalidJSONResponse(request, e)

        if json.get(FieldReportJSONKey.eventID.value, event_id) != event_id:
            return badRequestResponse(
                request,
                "Event ID mismatch: "
                f"{json[FieldReportJSONKey.eventID.value]} != {event_id}",
            )
        if json.get(FieldReportJSONKey.incidentNumber.value):
            return badRequestResponse(
                request,
                "New field report may not be attached to an incident: "
                f"{json[FieldReportJSONKey.incidentNumber.value]}",
            )

        user: IMSUser = request.user  # type: ignore[attr-defined]
        author = user.shortNames[0]
        now = DateTime.now(UTC)
        jsonNow = jsonObjectFromModelObject(now)

        # Set JSON event id
        # Set JSON field report number to 0
        # Set JSON field report created time to now

        for fieldReportKey in (
            FieldReportJSONKey.number,
            FieldReportJSONKey.created,
        ):
            if fieldReportKey.value in json:
                return badRequestResponse(
                    request,
                    f"New field report may not specify {fieldReportKey.value}",
                )

        json[FieldReportJSONKey.eventID.value] = event_id
        json[FieldReportJSONKey.number.value] = 0
        json[FieldReportJSONKey.created.value] = jsonNow

        # If not provided, set JSON report entries to an empty list

        if FieldReportJSONKey.reportEntries.value not in json:
            json[FieldReportJSONKey.reportEntries.value] = []

        # Set JSON report entry created time to now
        # Set JSON report entry author
        # Set JSON report entry automatic=False

        for entryJSON in json[FieldReportJSONKey.reportEntries.value]:
            for reportEntryKey in (
                ReportEntryJSONKey.created,
                ReportEntryJSONKey.author,
                ReportEntryJSONKey.automatic,
            ):
                if reportEntryKey.value in entryJSON:
                    return badRequestResponse(
                        request,
                        f"New report entry may not specify {reportEntryKey.value}",
                    )

            entryJSON[ReportEntryJSONKey.created.value] = jsonNow
            entryJSON[ReportEntryJSONKey.author.value] = author
            entryJSON[ReportEntryJSONKey.automatic.value] = False

        # Deserialize JSON field report

        try:
            fieldReport = modelObjectFromJSONObject(json, FieldReport)
        except JSONCodecError as e:
            return badRequestResponse(request, str(e))

        # Store the field report

        fieldReport = await self.config.store.createFieldReport(fieldReport, author)

        self._log.info(
            "User {author} created new field report #{fieldReport.number} via JSON",
            author=author,
            fieldReport=fieldReport,
        )
        self._log.debug(
            "New field report: {json}",
            json=jsonObjectFromModelObject(fieldReport),
        )

        request.setHeader(
            "X-IMS-Field-Report-Number",
            str(fieldReport.number),
        )
        request.setHeader(
            HeaderName.location.value,
            URLs.fieldReports.child(str(fieldReport.number)).asText(),
        )
        return noContentResponse(request)

    @router.route(_unprefix(URLs.fieldReport), methods=("HEAD", "GET"))
    async def readFieldReportResource(
        self, request: IRequest, event_id: str, field_report_number: str
    ) -> KleinSynchronousRenderable:
        """
        Field report endpoint.
        """
        try:
            fieldReportNumber = int(field_report_number)
        except ValueError:
            self.config.authProvider.authenticateRequest(request)
            return notFoundResponse(request)
        del field_report_number

        fieldReport = await self.config.store.fieldReportWithNumber(
            event_id, fieldReportNumber
        )

        await self.config.authProvider.authorizeRequestForFieldReport(
            request, fieldReport
        )

        text = jsonTextFromObject(jsonObjectFromModelObject(fieldReport))

        return jsonBytes(request, text.encode("utf-8"))

    @router.route(_unprefix(URLs.fieldReport), methods=("POST",))
    async def editFieldReportResource(
        self, request: IRequest, event_id: str, field_report_number: str
    ) -> KleinSynchronousRenderable:
        """
        Field report edit endpoint.
        """
        await self.config.authProvider.authorizeRequest(
            request, event_id, Authorization.writeFieldReports
        )

        user: IMSUser = request.user  # type: ignore[attr-defined]
        author = user.shortNames[0]

        try:
            fieldReportNumber = int(field_report_number)
        except ValueError:
            return notFoundResponse(request)
        del field_report_number

        store = self.config.store

        #
        # Attach to incident if requested
        #
        action = queryValue(request, "action")

        if action is not None:
            incidentNumberText = queryValue(request, "incident")

            if incidentNumberText is None:
                return invalidQueryResponse(request, "incident")

            try:
                incidentNumber = int(incidentNumberText)
            except ValueError:
                return invalidQueryResponse(request, "incident", incidentNumberText)

            if action == "attach":
                await store.attachFieldReportToIncident(
                    fieldReportNumber, event_id, incidentNumber, author
                )
            elif action == "detach":
                await store.detachFieldReportFromIncident(
                    fieldReportNumber, event_id, incidentNumber, author
                )
            else:
                return invalidQueryResponse(request, "action", action)

        #
        # Get the edits requested by the client
        #
        try:
            edits = objectFromJSONBytesIO(request.content)
        except JSONDecodeError as e:
            return invalidJSONResponse(request, e)

        if not isinstance(edits, dict):
            return badRequestResponse(request, "JSON field report must be a dictionary")

        if (
            edits.get(FieldReportJSONKey.number.value, fieldReportNumber)
            != fieldReportNumber
        ):
            return badRequestResponse(
                request, "Field report number may not be modified"
            )

        UNSET = object()

        created = edits.get(FieldReportJSONKey.created.value, UNSET)
        if created is not UNSET:
            return badRequestResponse(
                request, "Field report created time may not be modified"
            )

        async def applyEdit(
            json: Mapping[str, Any],
            key: Enum,
            setter: Callable[[str, int, Any, str], Awaitable[None]],
            cast: Callable[[Any], Any] | None = None,
        ) -> None:
            _cast: Callable[[Any], Any]
            if cast is None:

                def _cast(obj: Any) -> Any:
                    return obj

            else:
                _cast = cast
            value = json.get(key.value, UNSET)
            if value is not UNSET:
                await setter(event_id, fieldReportNumber, _cast(value), author)

        await applyEdit(
            edits,
            FieldReportJSONKey.summary,
            store.setFieldReport_summary,
        )

        jsonEntries = edits.get(FieldReportJSONKey.reportEntries.value, UNSET)
        if jsonEntries is not UNSET:
            now = DateTime.now(UTC)

            entries = (
                ReportEntry(
                    id=-1,
                    author=author,
                    text=jsonEntry[ReportEntryJSONKey.text.value],
                    created=now,
                    automatic=False,
                    stricken=False,
                )
                for jsonEntry in jsonEntries
            )

            await store.addReportEntriesToFieldReport(
                event_id, fieldReportNumber, entries, author
            )

        return noContentResponse(request)

    @router.route(_unprefix(URLs.fieldReport_reportEntry), methods=("POST",))
    async def editFieldReportReportEntryResource(
        self,
        request: IRequest,
        event_id: str,
        field_report_number: str,
        report_entry_id: str,
    ) -> KleinSynchronousRenderable:
        eventId = event_id
        fieldReportNumber = int(field_report_number)
        reportEntryId = int(report_entry_id)
        del event_id
        del field_report_number
        del report_entry_id

        fieldReport = await self.config.store.fieldReportWithNumber(
            eventId, fieldReportNumber
        )
        await self.config.authProvider.authorizeRequestForFieldReport(
            request, fieldReport
        )

        store = self.config.store

        user: IMSUser = request.user  # type: ignore[attr-defined]
        author = user.shortNames[0]

        #
        # Get the edits requested by the client
        #
        try:
            edits = objectFromJSONBytesIO(request.content)
        except JSONDecodeError as e:
            return invalidJSONResponse(request, e)

        if not isinstance(edits, dict):
            return badRequestResponse(request, "JSON incident must be a dictionary")

        if ReportEntryJSONKey.stricken.value in edits:
            newVal = bool(edits.get(ReportEntryJSONKey.stricken.value))
            await store.setFieldReportReportEntry_stricken(
                eventId, fieldReportNumber, reportEntryId, newVal, author
            )
        else:
            self._log.info("no key in request")

        return noContentResponse(request)

    @router.route(_unprefix(URLs.acl), methods=("HEAD", "GET"))
    async def readAdminAccessResource(
        self, request: IRequest
    ) -> KleinSynchronousRenderable:
        """
        Admin access control endpoint.
        """
        await self.config.authProvider.authorizeRequest(
            request, None, Authorization.imsAdmin
        )

        store = self.config.store

        acl = {}
        for event in await store.events():
            eventID = event.id
            readers: Iterable[AccessEntry] = await store.readers(eventID)
            writers: Iterable[AccessEntry] = await store.writers(eventID)
            reporters: Iterable[AccessEntry] = await store.reporters(eventID)
            acl[eventID] = {
                "readers": [jsonObjectFromModelObject(ae) for ae in readers],
                "writers": [jsonObjectFromModelObject(ae) for ae in writers],
                "reporters": [jsonObjectFromModelObject(ae) for ae in reporters],
            }
        return jsonTextFromObject(acl)

    @router.route(_unprefix(URLs.acl), methods=("POST",))
    async def editAdminAccessResource(
        self, request: IRequest
    ) -> KleinSynchronousRenderable:
        """
        Admin access control edit endpoint.
        """
        await self.config.authProvider.authorizeRequest(
            request, None, Authorization.imsAdmin
        )

        store = self.config.store

        try:
            edits = objectFromJSONBytesIO(request.content)
        except JSONDecodeError as e:
            return invalidJSONResponse(request, e)

        for eventID, acl in edits.items():
            if "readers" in acl:
                readers = tuple(
                    modelObjectFromJSONObject(ae, AccessEntry) for ae in acl["readers"]
                )
                await store.setReaders(eventID, readers)
            if "writers" in acl:
                writers = tuple(
                    modelObjectFromJSONObject(ae, AccessEntry) for ae in acl["writers"]
                )
                await store.setWriters(eventID, writers)
            if "reporters" in acl:
                reporters = tuple(
                    modelObjectFromJSONObject(ae, AccessEntry)
                    for ae in acl["reporters"]
                )
                await store.setReporters(eventID, reporters)

        return noContentResponse(request)

    @router.route(_unprefix(URLs.streets), methods=("HEAD", "GET"))
    async def readStreetsResource(
        self, request: IRequest
    ) -> KleinSynchronousRenderable:
        """
        Street list endpoint.
        """
        store = self.config.store

        async def authorizedEvents() -> AsyncIterable[Event]:
            for event in await store.events():
                try:
                    await self.config.authProvider.authorizeRequest(
                        request, event.id, Authorization.readIncidents
                    )
                except NotAuthorizedError:
                    pass
                else:
                    yield event

        return jsonBytes(
            request,
            jsonTextFromObject(
                {
                    event.id: await store.concentricStreets(event.id)
                    async for event in authorizedEvents()
                }
            ).encode("utf-8"),
        )

    @router.route(_unprefix(URLs.streets), methods=("POST",))
    async def editStreetsResource(
        self, request: IRequest
    ) -> KleinSynchronousRenderable:
        """
        Street list edit endpoint.
        """
        await self.config.authProvider.authorizeRequest(
            request, None, Authorization.imsAdmin
        )

        store = self.config.store

        try:
            edits = objectFromJSONBytesIO(request.content)
        except JSONDecodeError as e:
            return invalidJSONResponse(request, e)

        for eventID in edits.keys():
            existing = await store.concentricStreets(eventID)

            for _streetID, _streetName in existing.items():
                raise NotAuthorizedError("Removal of streets is not allowed.")

        for eventID, streets in edits.items():
            existing = await store.concentricStreets(eventID)

            for streetID, streetName in streets.items():
                if streetID not in existing:
                    await store.createConcentricStreet(eventID, streetID, streetName)

        return noContentResponse(request)

    @router.route(_unprefix(URLs.eventSource), methods=("GET",))
    def eventSourceResource(self, request: IRequest) -> KleinRenderable:
        """
        HTML5 EventSource endpoint.
        """
        self._log.debug("Event source connected: {id}", id=id(request))

        # Note that we don't read the Last-Event-Id header, which browsers provide
        # on automated reconnection. We don't need it.

        # Clear the cookies on the response. Without this here, the eventsource
        # call will often return Set-Cookie values that lead clients to stomp
        # over authenticated session cookies with unauthenticated ones.
        request.cookies = []  # type: ignore[attr-defined]

        request.setHeader(HeaderName.contentType.value, ContentType.eventStream.value)

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
        d = request.notifyFinish()  # type: ignore[attr-defined]
        d.addCallbacks(finished, disconnected)

        # Return an unfired deferred, so the connection doesn't close on this
        # end...
        return Deferred()
