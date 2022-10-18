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
Incident tests for :mod:`ranger-ims-server.store`
"""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import datetime as DateTime
from datetime import timedelta as TimeDelta
from datetime import timezone as TimeZone
from typing import Any, Optional, cast

from attr import fields as attrFields

from ims.ext.trial import asyncAsDeferred
from ims.model import (
    Event,
    Incident,
    IncidentPriority,
    IncidentState,
    Location,
    ReportEntry,
    RodGarettAddress,
)

from .._exceptions import NoSuchIncidentError, StorageError
from .base import DataStoreTests, TestDataStoreABC


__all__ = ()


anEvent = Event(id="foo")
anEvent2 = Event(id="bar")

# Note: we add a TimeDelta to the created attribute of objects so that they
# don't have timestamps that are within the time resolution of some back-end
# data stores.

aNewIncident = Incident(
    eventID=anEvent.id,
    number=0,
    created=DateTime.now(TimeZone.utc) + TimeDelta(seconds=1),
    state=IncidentState.new,
    priority=IncidentPriority.normal,
    summary="A thing happened",
    location=Location(name="There", address=None),
    rangerHandles=(),
    incidentTypes=(),
    reportEntries=(),
    incidentReportNumbers=(),
)

anIncident1 = Incident(
    eventID=anEvent.id,
    number=1,
    created=DateTime.now(TimeZone.utc) + TimeDelta(seconds=2),
    state=IncidentState.new,
    priority=IncidentPriority.normal,
    summary="A thing happened",
    location=Location(name="There", address=None),
    rangerHandles=(),
    incidentTypes=(),
    reportEntries=(),
    incidentReportNumbers=(),
)

anIncident2 = Incident(
    eventID=anEvent2.id,
    number=325,
    created=DateTime.now(TimeZone.utc) + TimeDelta(seconds=3),
    state=IncidentState.new,
    priority=IncidentPriority.normal,
    summary="Another thing happened",
    location=Location(name="Here", address=None),
    rangerHandles=(),
    incidentTypes=(),
    reportEntries=(),
    incidentReportNumbers=(),
)

aReportEntry = ReportEntry(
    created=DateTime.now(TimeZone.utc) + TimeDelta(seconds=4),
    author="Hubcap",
    automatic=False,
    text="Hello",
)

aReportEntry1 = ReportEntry(
    created=DateTime.now(TimeZone.utc) + TimeDelta(seconds=5),
    author="Bucket",
    automatic=False,
    text="This happened",
)

aReportEntry2 = ReportEntry(
    created=DateTime.now(TimeZone.utc) + TimeDelta(seconds=6),
    author="Bucket",
    automatic=False,
    text="That happened",
)


class DataStoreIncidentTests(DataStoreTests):
    """
    Tests for :class:`IMSDataStore` incident access.
    """

    @asyncAsDeferred
    async def test_incidents(self) -> None:
        """
        :meth:`IMSDataStore.incidents` returns all incidents.
        """
        for _incidents in (
            [],
            [anIncident1],
            [anIncident1, anIncident2],
        ):
            incidents = tuple(cast(Iterable[Incident], _incidents))

            events: dict[str, dict[int, Incident]] = defaultdict(defaultdict)

            store = await self.store()

            for incident in incidents:
                await store.storeIncident(incident)

                events[incident.eventID][incident.number] = incident

            found: set[tuple[str, int]] = set()
            for eventID in events:
                for retrieved in await store.incidents(eventID):
                    self.assertIncidentsEqual(
                        store, retrieved, events[eventID][retrieved.number]
                    )
                    found.add((eventID, retrieved.number))

            self.assertEqual(found, {(i.eventID, i.number) for i in incidents})

    @asyncAsDeferred
    async def test_incidents_sameEvent(self) -> None:
        """
        :meth:`IMSDataStore.incidents` returns all incidents.
        """
        for _incidents in (
            [anIncident1],
            [anIncident1, anIncident2.replace(eventID=anIncident1.eventID)],
        ):
            incidents = frozenset(_incidents)

            store = await self.store()

            eventID: Optional[str] = None

            for incident in incidents:
                eventID = incident.eventID

                await store.storeIncident(incident)

            assert eventID is not None

            retrieved = await store.incidents(eventID)

            for r, i in zip(sorted(retrieved), sorted(incidents)):
                self.assertIncidentsEqual(store, r, i)

    @asyncAsDeferred
    async def test_incidents_error(self) -> None:
        """
        :meth:`IMSDataStore.incidents` raises :exc:`StorageError` when the
        store raises an exception.
        """
        store = await self.store()
        await store.createEvent(anEvent)
        store.bringThePain()

        try:
            await store.incidents(anEvent.id)
        except StorageError as e:
            self.assertEqual(str(e), store.exceptionMessage)
        else:
            self.fail("StorageError not raised")

    @asyncAsDeferred
    async def test_incidentWithNumber(self) -> None:
        """
        :meth:`IMSDataStore.incidentWithNumber` returns the specified incident.
        """
        for incident in (anIncident1, anIncident2):
            store = await self.store()

            await store.storeIncident(incident)

            retrieved = await store.incidentWithNumber(
                incident.eventID, incident.number
            )

            self.assertIncidentsEqual(store, retrieved, incident)

    @asyncAsDeferred
    async def test_incidentWithNumber_notFound(self) -> None:
        """
        :meth:`IMSDataStore.incidentWithNumber` raises
        :exc:`NoSuchIncidentError` when the given incident number is not found.
        """
        store = await self.store()
        await store.createEvent(anEvent)

        try:
            await store.incidentWithNumber(anEvent.id, 1)
        except NoSuchIncidentError:
            pass
        else:
            self.fail("NoSuchIncidentError not raised")

    @asyncAsDeferred
    async def test_incidentWithNumber_tooBig(self) -> None:
        """
        :meth:`IMSDataStore.incidentWithNumber` raises
        :exc:`NoSuchIncidentError` when the given incident number is too large
        for the store.
        """
        store = await self.store()
        await store.createEvent(anEvent)

        try:
            await store.incidentWithNumber(
                anEvent.id, store.maxIncidentNumber + 1
            )
        except NoSuchIncidentError:
            pass
        else:
            self.fail("NoSuchIncidentError not raised")

    @asyncAsDeferred
    async def test_incidentWithNumber_error(self) -> None:
        """
        :meth:`IMSDataStore.incidentWithNumber` raises :exc:`StorageError` when
        the store raises an exception.
        """
        store = await self.store()
        await store.createEvent(anEvent)
        store.bringThePain()

        try:
            await store.incidentWithNumber(anEvent.id, 1)
        except StorageError as e:
            self.assertEqual(str(e), store.exceptionMessage)
        else:
            self.fail("StorageError not raised")

    @asyncAsDeferred
    async def test_createIncident(self) -> None:
        """
        :meth:`IMSDataStore.createIncident` creates the given incident.
        """
        for _data in (
            (),
            ((anIncident1.replace(number=0), "Hubcap"),),
            (
                (anIncident1.replace(number=0), "Hubcap"),
                (anIncident2.replace(number=0), "Bucket"),
            ),
        ):
            data = cast(Iterable[tuple[Incident, str]], _data)

            store = await self.store()

            createdEvents: set[Event] = set()
            createdIncidentTypes: set[str] = set()
            createdConcentricStreets: dict[Event, set[str]] = defaultdict(set)

            expectedStoredIncidents: set[Incident] = set()
            nextNumbers: dict[Event, int] = {}

            for incident, author in data:
                event = Event(id=incident.eventID)

                if event not in createdEvents:
                    await store.createEvent(event)
                    createdEvents.add(event)

                for incidentType in incident.incidentTypes:
                    if incidentType not in createdIncidentTypes:
                        await store.createIncidentType(incidentType)
                        createdIncidentTypes.add(incidentType)

                address = incident.location.address
                if isinstance(address, RodGarettAddress):
                    concentric = address.concentric
                    if (
                        concentric is not None
                        and concentric not in createdConcentricStreets[event]
                    ):
                        await store.createConcentricStreet(
                            event.id, concentric, "Sesame Street"
                        )
                        createdConcentricStreets[event].add(concentric)

                retrieved = await store.createIncident(
                    incident=incident, author=author
                )

                # The returned incident should be the same, except for modified
                # number
                expectedStoredIncident = incident.replace(
                    number=nextNumbers.setdefault(event, 1)
                )
                self.assertIncidentsEqual(
                    store,
                    retrieved,
                    expectedStoredIncident,
                    ignoreAutomatic=True,
                )

                # Add to set of stored incidents
                expectedStoredIncidents.add(expectedStoredIncident)
                nextNumbers[event] += 1

            # Stored incidents should be contain incidents stored above
            for event in createdEvents:
                expectedIncidents = sorted(
                    i for i in expectedStoredIncidents if i.eventID == event.id
                )
                storedIncidents = sorted(await store.incidents(event.id))

                self.assertEqual(
                    len(storedIncidents),
                    len(expectedIncidents),
                    f"{storedIncidents} != {expectedIncidents}",
                )

                for stored, expected in zip(storedIncidents, expectedIncidents):
                    self.assertIncidentsEqual(
                        store, stored, expected, ignoreAutomatic=True
                    )

    @asyncAsDeferred
    async def test_createIncident_error(self) -> None:
        """
        :meth:`IMSDataStore.createIncident` raises :exc:`StorageError` when the
        store raises an exception.
        """
        store = await self.store()
        await store.createEvent(Event(id=aNewIncident.eventID))
        store.bringThePain()

        try:
            await store.createIncident(aNewIncident, "Hubcap")
        except StorageError as e:
            self.assertEqual(str(e), store.exceptionMessage)
        else:
            self.fail("StorageError not raised")

    @asyncAsDeferred
    async def test_setIncident_priority_error(self) -> None:
        """
        :meth:`IMSDataStore.setIncident_priority` raises :exc:`StorageError`
        when the store raises an exception.
        """
        store = await self.store()
        await store.storeIncident(anIncident1)
        store.bringThePain()

        try:
            await store.setIncident_priority(
                anIncident1.eventID,
                anIncident1.number,
                IncidentPriority.high,
                "Bucket",
            )
        except StorageError as e:
            self.assertEqual(str(e), store.exceptionMessage)
        else:
            self.fail("StorageError not raised")

    async def _test_setIncidentAttribute(
        self,
        incident: Incident,
        methodName: str,
        attributeName: str,
        value: Any,
    ) -> None:
        store = await self.store()

        await store.storeIncident(incident)

        setter = getattr(store, methodName)

        # For concentric streets, we need to make sure they exist first.
        if attributeName == "location.address.concentric":
            await store.storeConcentricStreet(
                incident.eventID,
                value,
                "Concentric Street",
                ignoreDuplicates=True,
            )

        # For incident types, we need to make sure they exist first.
        if attributeName == "incidentTypes":
            for incidentType in frozenset(value) - frozenset(
                incident.incidentTypes
            ):
                await store.createIncidentType(incidentType)

        await setter(incident.eventID, incident.number, value, "Hubcap")

        retrieved = await store.incidentWithNumber(
            incident.eventID, incident.number
        )

        # Normalize location if we're updating the address.
        # Don't normalize before calling the setter; we want to test that
        # giving it un-normalized data works.
        if attributeName.startswith("location.address."):
            incident = store.normalizeIncidentAddress(incident)

        # Replace the specified incident attribute with the given value.
        # This is a bit complex because we're recursing into sub-attributes.
        attrPath = attributeName.split(".")
        values = [incident]
        for a in attrPath[:-1]:
            values.append(getattr(values[-1], a))
        values.append(value)
        for a in reversed(attrPath):
            v = values.pop()
            values[-1] = values[-1].replace(**{a: v})
        incident = values[0]

        self.assertIncidentsEqual(
            store, retrieved, incident, ignoreAutomatic=True
        )

    @asyncAsDeferred
    async def test_setIncident_priority(self) -> None:
        """
        :meth:`IMSDataStore.setIncident_priority` updates the priority for the
        given incident in the data store.
        """
        for priority in IncidentPriority:
            for incident in (anIncident1, anIncident2):
                await self._test_setIncidentAttribute(
                    incident, "setIncident_priority", "priority", priority
                )

    @asyncAsDeferred
    async def test_setIncident_state(self) -> None:
        """
        :meth:`IMSDataStore.setIncident_state` updates the state for the
        incident with the given number in the data store.
        """
        for state in IncidentState:
            for incident in (anIncident1, anIncident2):
                await self._test_setIncidentAttribute(
                    incident, "setIncident_state", "state", state
                )

    @asyncAsDeferred
    async def test_setIncident_summary(self) -> None:
        """
        :meth:`IMSDataStore.setIncident_summary` updates the summary for the
        given incident in the data store.
        """
        for incident, summary in (
            (anIncident1, "foo bar"),
            (anIncident2, "quux bang"),
        ):
            await self._test_setIncidentAttribute(
                incident, "setIncident_summary", "summary", summary
            )

    @asyncAsDeferred
    async def test_setIncident_locationName(self) -> None:
        """
        :meth:`IMSDataStore.setIncident_locationName` updates the location name
        for the given incident in the data store.
        """
        for incident, name in (
            (anIncident1, "foo bar"),
            (anIncident2, "quux bang"),
        ):
            await self._test_setIncidentAttribute(
                incident, "setIncident_locationName", "location.name", name
            )

    @asyncAsDeferred
    async def test_setIncident_locationConcentricStreet(self) -> None:
        """
        :meth:`IMSDataStore.setIncident_locationConcentricStreet` updates the
        location concentric street for the given incident in the data store.
        """
        for incident, streetID in (
            (anIncident1, "foo bar"),
            (anIncident2, "quux bang"),
        ):
            await self._test_setIncidentAttribute(
                incident,
                "setIncident_locationConcentricStreet",
                "location.address.concentric",
                streetID,
            )

    @asyncAsDeferred
    async def test_setIncident_locationRadialHour(self) -> None:
        """
        :meth:`IMSDataStore.setIncident_locationRadialHour` updates the
        location radial hour for the given incident in the data store.
        """
        for incident, radialHour in (
            (anIncident1, 3),
            (anIncident2, 9),
        ):
            await self._test_setIncidentAttribute(
                incident,
                "setIncident_locationRadialHour",
                "location.address.radialHour",
                radialHour,
            )

    @asyncAsDeferred
    async def test_setIncident_locationRadialMinute(self) -> None:
        """
        :meth:`IMSDataStore.setIncident_locationRadialMinute` updates the
        location radial minute for the given incident in the data store.
        """
        for incident, radialMinute in (
            (anIncident1, 0),
            (anIncident2, 15),
        ):
            await self._test_setIncidentAttribute(
                incident,
                "setIncident_locationRadialMinute",
                "location.address.radialMinute",
                radialMinute,
            )

    @asyncAsDeferred
    async def test_setIncident_locationDescription(self) -> None:
        """
        :meth:`IMSDataStore.setIncident_locationDescription` updates the
        location description for the given incident in the data store.
        """
        incident = anIncident1

        for description in ("", "foo bar", "beep boop"):
            await self._test_setIncidentAttribute(
                incident,
                "setIncident_locationDescription",
                "location.address.description",
                description,
            )

    @asyncAsDeferred
    async def test_setIncident_rangers(self) -> None:
        """
        :meth:`IMSDataStore.setIncident_rangers` updates the ranger handles for
        the given incident in the data store.
        """
        incident = anIncident1

        for rangerHandles in (
            (),
            ("Hubcap",),
            ("Hubcap", "Bucket"),
        ):
            await self._test_setIncidentAttribute(
                incident,
                "setIncident_rangers",
                "rangerHandles",
                rangerHandles,
            )

    @asyncAsDeferred
    async def test_setIncident_rangers_error(self) -> None:
        """
        :meth:`IMSDataStore.setIncident_rangers` raises :exc:`StorageError`
        when the store raises an exception.
        """
        store = await self.store()
        await store.storeIncident(anIncident1)
        store.bringThePain()

        try:
            await store.setIncident_rangers(
                anIncident1.eventID,
                anIncident1.number,
                ("Hubcap", "Dingle"),
                "Bucket",
            )
        except StorageError as e:
            self.assertEqual(str(e), store.exceptionMessage)
        else:
            self.fail("StorageError not raised")

    @asyncAsDeferred
    async def test_setIncident_incidentTypes(self) -> None:
        """
        :meth:`IMSDataStore.setIncident_rangers` updates the ranger handles for
        the given incident in the data store.
        """
        for incidentTypes in (
            (),
            ("MOOP",),
            ("Medical", "Fire"),
        ):
            await self._test_setIncidentAttribute(
                anIncident1,
                "setIncident_incidentTypes",
                "incidentTypes",
                incidentTypes,
            )

    @asyncAsDeferred
    async def test_setIncident_incidentTypes_error(self) -> None:
        """
        :meth:`IMSDataStore.setIncident_incidentTypes` raises
        :exc:`StorageError` when the store raises an exception.
        """
        store = await self.store()
        await store.storeIncident(anIncident1)
        store.bringThePain()

        try:
            await store.setIncident_incidentTypes(
                anIncident1.eventID,
                anIncident1.number,
                ("Fun", "Boring"),
                "Bucket",
            )
        except StorageError as e:
            self.assertEqual(str(e), store.exceptionMessage)
        else:
            self.fail("StorageError not raised")

    @asyncAsDeferred
    async def test_addReportEntriesToIncident(self) -> None:
        """
        :meth:`IMSDataStore.addReportEntriesToIncident` adds the given report
        entries to the given incident in the data store.
        """
        for incident in (anIncident1, anIncident2):
            for entriesBy in (
                ((), "Joe Ranger"),
                ((aReportEntry,), aReportEntry.author),
                ((aReportEntry1, aReportEntry2), aReportEntry1.author),
            ):
                reportEntries, author = cast(
                    tuple[Sequence[ReportEntry], str],
                    entriesBy,
                )

                # Store test data
                store = await self.store()
                await store.createEvent(Event(id=incident.eventID))
                await store.storeIncident(incident)

                # Fetch incident back so we have the same data as the DB
                incident = await store.incidentWithNumber(
                    incident.eventID, incident.number
                )

                # Add report entries
                await store.addReportEntriesToIncident(
                    incident.eventID, incident.number, reportEntries, author
                )

                # Get the updated incident with the new report entries
                updatedIncident = await store.incidentWithNumber(
                    incident.eventID, incident.number
                )

                # Updated number of incidents should be original plus new
                self.assertEqual(
                    len(updatedIncident.reportEntries),
                    len(incident.reportEntries) + len(reportEntries),
                )

                # Updated entries minus the original entries == the added
                # entries
                updatedNewEntries = sorted(updatedIncident.reportEntries)
                for entry in incident.reportEntries:
                    updatedNewEntries.remove(entry)

                # New entries should be the same as the ones we added
                self.assertTrue(
                    store.reportEntriesEqual(
                        updatedNewEntries, sorted(reportEntries)
                    ),
                    f"{updatedNewEntries} != {reportEntries}",
                )

    @asyncAsDeferred
    async def test_addReportEntriesToIncident_automatic(self) -> None:
        """
        :meth:`IMSDataStore.addReportEntriesToIncident` raises
        :exc:`ValueError` when given automatic report entries.
        """
        store = await self.store()
        await store.storeIncident(anIncident1)

        reportEntry = aReportEntry.replace(automatic=True)

        try:
            await store.addReportEntriesToIncident(
                anIncident1.eventID,
                anIncident1.number,
                (reportEntry,),
                reportEntry.author,
            )
        except ValueError as e:
            self.assertIn(" may not be created by user ", str(e))
        else:
            self.fail("StorageError not raised")

    @asyncAsDeferred
    async def test_addReportEntriesToIncident_wrongAuthor(self) -> None:
        """
        :meth:`IMSDataStore.addReportEntriesToIncident` raises
        :exc:`ValueError` when given report entries with an author that does
        not match the author that is adding the entries.
        """
        store = await self.store()
        await store.storeIncident(anIncident1)

        otherAuthor = f"not{aReportEntry.author}"

        try:
            await store.addReportEntriesToIncident(
                anIncident1.eventID,
                anIncident1.number,
                (aReportEntry,),
                otherAuthor,
            )
        except ValueError as e:
            self.assertEndsWith(str(e), f" has author != {otherAuthor}")
        else:
            self.fail("StorageError not raised")

    @asyncAsDeferred
    async def test_addReportEntriesToIncident_error(self) -> None:
        """
        :meth:`IMSDataStore.addReportEntriesToIncident` raises
        :exc:`StorageError` when the store raises an exception.
        """
        store = await self.store()
        await store.storeIncident(anIncident1)
        store.bringThePain()

        try:
            await store.addReportEntriesToIncident(
                anIncident1.eventID,
                anIncident1.number,
                (aReportEntry,),
                aReportEntry.author,
            )
        except StorageError as e:
            self.assertEqual(str(e), store.exceptionMessage)
        else:
            self.fail("StorageError not raised")

    def assertIncidentsEqual(
        self,
        store: TestDataStoreABC,
        incidentA: Incident,
        incidentB: Incident,
        ignoreAutomatic: bool = False,
    ) -> None:
        if incidentA != incidentB:
            messages = []

            for attribute in attrFields(Incident):
                name = attribute.name
                valueA = getattr(incidentA, name)
                valueB = getattr(incidentB, name)

                if name == "created":
                    if store.dateTimesEqual(valueA, valueB):
                        continue
                    else:
                        messages.append(f"{name} delta: {valueA - valueB}")
                elif name == "reportEntries":
                    if store.reportEntriesEqual(
                        valueA, valueB, ignoreAutomatic
                    ):
                        continue

                if valueA != valueB:
                    messages.append(f"{name} {valueA!r} != {valueB!r}")

            if messages:
                self.fail("Incidents do not match:\n" + "\n".join(messages))
