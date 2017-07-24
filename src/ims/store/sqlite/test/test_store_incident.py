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
Tests for :mod:`ranger-ims-server.store.sqlite._store`
"""

from collections import defaultdict
from datetime import datetime as DateTime, timezone as TimeZone
from typing import (
    Any, Dict, FrozenSet, Iterable, Optional, Set, Tuple
)

from attr import fields as attrFields

from hypothesis import assume, given
from hypothesis.strategies import frozensets, lists, text, tuples

from ims.ext.sqlite import SQLITE_MAX_INT
from ims.model import (
    Event, Incident, IncidentPriority, IncidentState,
    Location, ReportEntry, RodGarettAddress,
)
from ims.model.strategies import (
    concentricStreetIDs, incidentLists, incidentPriorities, incidentStates,
    incidentSummaries, incidentTypesText, incidents, locationNames,
    radialHours, radialMinutes, rangerHandles, reportEntries,
)

from .base import (
    DataStoreTests, dateTimesEqualish, normalizeAddress, reportEntriesEqualish,
    storeConcentricStreet,
)
from ..._exceptions import NoSuchIncidentError, StorageError

Dict, Event, Optional, Set  # silence linter


__all__ = ()



class DataStoreIncidentTests(DataStoreTests):
    """
    Tests for :class:`DataStore` incident access.
    """

    @given(incidentLists(maxNumber=SQLITE_MAX_INT, averageSize=3))
    def test_incidents(self, incidents: Iterable[Incident]) -> None:
        """
        :meth:`DataStore.incidents` returns all incidents.
        """
        incidents = tuple(incidents)

        events: Dict[Event, Dict[int, Incident]] = defaultdict(defaultdict)

        store = self.store()

        for incident in incidents:
            assume(incident.number not in events[incident.event])

            self.storeIncident(store, incident)

            events[incident.event][incident.number] = incident

        found: Set[Tuple[Event, int]] = set()
        for event in events:
            for retrieved in self.successResultOf(
                store.incidents(event)
            ):
                self.assertIncidentsEqual(
                    retrieved, events[event][retrieved.number]
                )
                found.add((event, retrieved.number))

        self.assertEqual(found, set(((i.event, i.number) for i in incidents)))


    @given(
        incidentLists(
            event=Event("Foo"), maxNumber=SQLITE_MAX_INT,
            minSize=2, averageSize=3,
        ),
    )
    def test_incidents_sameEvent(self, incidents: Iterable[Incident]) -> None:
        """
        :meth:`DataStore.incidents` returns all incidents.
        """
        incidents = frozenset(incidents)

        store = self.store()

        event: Optional[Event] = None

        for incident in incidents:
            event = incident.event

            self.storeIncident(store, incident)

        assert event is not None

        retrieved = self.successResultOf(store.incidents(event))

        for r, i in zip(sorted(retrieved), sorted(incidents)):
            self.assertIncidentsEqual(r, i)


    def test_incidents_error(self) -> None:
        """
        :meth:`DataStore.incidents` raises :exc:`StorageError` when SQLite
        raises an exception.
        """
        event = Event(id="foo")
        store = self.store()
        self.successResultOf(store.createEvent(event))
        store.bringThePain()

        f = self.failureResultOf(store.incidents(event))
        self.assertEqual(f.type, StorageError)


    @given(incidents(maxNumber=SQLITE_MAX_INT))
    def test_incidentWithNumber(self, incident: Incident) -> None:
        """
        :meth:`DataStore.incidentWithNumber` return the specified incident.
        """
        store = self.store()

        self.storeIncident(store, incident)

        retrieved = self.successResultOf(
            store.incidentWithNumber(incident.event, incident.number)
        )

        self.assertIncidentsEqual(retrieved, incident)


    def test_incidentWithNumber_notFound(self) -> None:
        """
        :meth:`DataStore.incidentWithNumber` raises :exc:`NoSuchIncidentError`
        when the given incident number is not found.
        """
        event = Event(id="foo")
        store = self.store()
        self.successResultOf(store.createEvent(event))

        f = self.failureResultOf(
            store.incidentWithNumber(event, 1)
        )
        self.assertEqual(f.type, NoSuchIncidentError)


    def test_incidentWithNumber_tooBig(self) -> None:
        """
        :meth:`DataStore.incidentWithNumber` raises :exc:`NoSuchIncidentError`
        when the given incident number is too large for SQLite.
        """
        event = Event(id="foo")
        store = self.store()
        self.successResultOf(store.createEvent(event))

        f = self.failureResultOf(
            store.incidentWithNumber(event, SQLITE_MAX_INT + 1)
        )
        f.printTraceback()
        self.assertEqual(f.type, NoSuchIncidentError)


    def test_incidentWithNumber_error(self) -> None:
        """
        :meth:`DataStore.incidentWithNumber` raises :exc:`StorageError` when
        SQLite raises an exception.
        """
        event = Event(id="foo")
        store = self.store()
        self.successResultOf(store.createEvent(event))
        store.bringThePain()

        f = self.failureResultOf(store.incidentWithNumber(event, 1))
        self.assertEqual(f.type, StorageError)


    @given(lists(tuples(incidents(new=True), rangerHandles()), average_size=2))
    def test_createIncident(
        self, data: Iterable[Tuple[Incident, str]]
    ) -> None:
        """
        :meth:`DataStore.createIncident` creates the given incident.
        """
        store = self.store()

        createdEvents: Set[Event] = set()
        createdIncidentTypes: Set[str] = set()
        createdConcentricStreets: Dict[Event, Set[str]] = defaultdict(set)

        expectedStoredIncidents: Set[Incident] = set()
        nextNumbers: Dict[Event, int] = {}

        for incident, author in data:
            event = incident.event

            if event not in createdEvents:
                self.successResultOf(store.createEvent(event))
                createdEvents.add(event)

            for incidentType in incident.incidentTypes:
                if incidentType not in createdIncidentTypes:
                    self.successResultOf(
                        store.createIncidentType(incidentType)
                    )
                    createdIncidentTypes.add(incidentType)

            address = incident.location.address
            if isinstance(address, RodGarettAddress):
                concentric = address.concentric
                if (
                    concentric is not None and
                    concentric not in createdConcentricStreets[event]
                ):
                    self.successResultOf(
                        store.createConcentricStreet(
                            event, concentric, "Sesame Street"
                        )
                    )
                    createdConcentricStreets[event].add(concentric)

            returnedIncident = self.successResultOf(
                store.createIncident(incident=incident, author=author)
            )

            # The returned incident should be the same, except for modified
            # number
            expectedStoredIncident = incident.replace(
                number=nextNumbers.setdefault(event, 1)
            )
            self.assertIncidentsEqual(
                returnedIncident, expectedStoredIncident, ignoreAutomatic=True
            )

            # Add to set of stored incidents
            expectedStoredIncidents.add(expectedStoredIncident)
            nextNumbers[event] += 1

        # Stored incidents should be contain incidents stored above
        for event in createdEvents:
            expectedIncidents = sorted(
                i for i in expectedStoredIncidents if i.event == event
            )
            storedIncidents = sorted(
                self.successResultOf(store.incidents(event=event))
            )

            if len(storedIncidents) != len(expectedIncidents):
                import pdb
                pdb.set_trace()

            storedIncidents = sorted(
                self.successResultOf(store.incidents(event=event))
            )

            self.assertEqual(
                len(storedIncidents), len(expectedIncidents),
                "{} != {}".format(storedIncidents, expectedIncidents)
            )

            for stored, expected in zip(storedIncidents, expectedIncidents):
                self.assertIncidentsEqual(
                    stored, expected, ignoreAutomatic=True
                )


    def test_createIncident_error(self) -> None:
        """
        :meth:`DataStore.createIncident` raises :exc:`StorageError` when SQLite
        raises an exception.
        """
        event = Event(id="foo")
        store = self.store()
        self.successResultOf(store.createEvent(event))
        store.bringThePain()

        f = self.failureResultOf(store.createIncident(
            Incident(
                event=Event("foo"),
                number=0,
                created=DateTime.now(TimeZone.utc),
                state=IncidentState.new, priority=IncidentPriority.normal,
                summary="A thing happened",
                location=Location(name="There", address=None),
                rangerHandles=(), incidentTypes=(), reportEntries=(),
            ),
            "Hubcap")
        )
        self.assertEqual(f.type, StorageError)


    def test_setIncident_priority_error(self) -> None:
        """
        :meth:`DataStore.setIncident_priority` raises ...
        """
        event = Event(id="foo")
        store = self.store()
        self.successResultOf(store.createEvent(event))
        incident = self.successResultOf(store.createIncident(
            Incident(
                event=Event("foo"),
                number=0,
                created=DateTime.now(TimeZone.utc),
                state=IncidentState.new, priority=IncidentPriority.normal,
                summary="A thing happened",
                location=Location(name="There", address=None),
                rangerHandles=(), incidentTypes=(), reportEntries=(),
            ),
            "Hubcap")
        )
        store.bringThePain()

        f = self.failureResultOf(
            store.setIncident_priority(
                event, incident.number, IncidentPriority.high, "Bucket"
            )
        )
        self.assertEqual(f.type, StorageError)


    def _test_setIncidentAttribute(
        self, incident: Incident,
        methodName: str, attributeName: str, value: Any
    ) -> None:
        store = self.store()

        self.storeIncident(store, incident)

        setter = getattr(store, methodName)

        # For concentric streets, we need to make sure they exist first.
        if attributeName == "location.address.concentric":
            storeConcentricStreet(
                store._db, incident.event, value, "Concentric Street",
                ignoreDuplicates=True,
            )

        # For incident types, we need to make sure they exist first.
        if attributeName == "incidentTypes":
            for incidentType in (
                frozenset(value) - frozenset(incident.incidentTypes)
            ):
                self.successResultOf(store.createIncidentType(incidentType))

        self.successResultOf(
            setter(incident.event, incident.number, value, "Hubcap")
        )

        retrieved = self.successResultOf(
            store.incidentWithNumber(incident.event, incident.number)
        )

        # Normalize location if we're updating the address.
        # Don't normalize before calling the setter; we want to test that
        # giving it un-normalized data works.
        if attributeName.startswith("location.address."):
            incident = normalizeAddress(incident)

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

        self.assertIncidentsEqual(retrieved, incident, ignoreAutomatic=True)


    @given(incidents(new=True), incidentPriorities())
    def test_setIncident_priority(
        self, incident: Incident, priority: IncidentPriority
    ) -> None:
        """
        :meth:`DataStore.setIncident_priority` updates the priority for the
        given incident in the data store.
        """
        self._test_setIncidentAttribute(
            incident, "setIncident_priority", "priority", priority
        )


    @given(incidents(new=True), incidentStates())
    def test_setIncident_state(
        self, incident: Incident, state: IncidentState
    ) -> None:
        """
        :meth:`DataStore.setIncident_state` updates the state for the incident
        with the given number in the data store.
        """
        self._test_setIncidentAttribute(
            incident, "setIncident_state", "state", state
        )


    @given(incidents(new=True), incidentSummaries())
    def test_setIncident_summary(
        self, incident: Incident, summary: str
    ) -> None:
        """
        :meth:`DataStore.setIncident_summary` updates the summary for the
        given incident in the data store.
        """
        self._test_setIncidentAttribute(
            incident, "setIncident_summary", "summary", summary
        )


    @given(incidents(new=True), locationNames())
    def test_setIncident_locationName(
        self, incident: Incident, name: str
    ) -> None:
        """
        :meth:`DataStore.setIncident_locationName` updates the location name
        for the given incident in the data store.
        """
        self._test_setIncidentAttribute(
            incident, "setIncident_locationName", "location.name", name
        )


    @given(incidents(new=True), concentricStreetIDs())
    def test_setIncident_locationConcentricStreet(
        self, incident: Incident, streetID: str
    ) -> None:
        """
        :meth:`DataStore.setIncident_locationConcentricStreet` updates the
        location concentric street for the given incident in the data store.
        """
        self._test_setIncidentAttribute(
            incident, "setIncident_locationConcentricStreet",
            "location.address.concentric", streetID,
        )


    @given(incidents(new=True), radialHours())
    def test_setIncident_locationRadialHour(
        self, incident: Incident, radialHour: int
    ) -> None:
        """
        :meth:`DataStore.setIncident_locationRadialHour` updates the location
        radial hour for the given incident in the data store.
        """
        self._test_setIncidentAttribute(
            incident, "setIncident_locationRadialHour",
            "location.address.radialHour", radialHour,
        )


    @given(incidents(new=True), radialMinutes())
    def test_setIncident_locationRadialMinute(
        self, incident: Incident, radialMinute: int
    ) -> None:
        """
        :meth:`DataStore.setIncident_locationRadialMinute` updates the location
        radial minute for the given incident in the data store.
        """
        self._test_setIncidentAttribute(
            incident, "setIncident_locationRadialMinute",
            "location.address.radialMinute", radialMinute,
        )


    @given(incidents(new=True), text())
    def test_setIncident_locationDescription(
        self, incident: Incident, description: str
    ) -> None:
        """
        :meth:`DataStore.setIncident_locationDescription` updates the location
        description for the given incident in the data store.
        """
        self._test_setIncidentAttribute(
            incident, "setIncident_locationDescription",
            "location.address.description", description,
        )


    @given(incidents(new=True), lists(rangerHandles()))
    def test_setIncident_rangers(
        self, incident: Incident, rangerHandles: Iterable[str]
    ) -> None:
        """
        :meth:`DataStore.setIncident_rangers` updates the ranger handles for
        the given incident in the data store.
        """
        self._test_setIncidentAttribute(
            incident, "setIncident_rangers", "rangerHandles", rangerHandles,
        )


    def test_setIncident_rangers_error(self) -> None:
        """
        :meth:`DataStore.setIncident_rangers` raises :exc:`StorageError` when
        SQLite raises an exception.
        """
        event = Event(id="foo")
        store = self.store()
        self.successResultOf(store.createEvent(event))
        incident = self.successResultOf(store.createIncident(
            Incident(
                event=Event("foo"),
                number=0,
                created=DateTime.now(TimeZone.utc),
                state=IncidentState.new, priority=IncidentPriority.normal,
                summary="A thing happened",
                location=Location(name="There", address=None),
                rangerHandles=(), incidentTypes=(), reportEntries=(),
            ),
            "Hubcap")
        )
        store.bringThePain()

        f = self.failureResultOf(
            store.setIncident_rangers(
                event, incident.number, ("Hubcap", "Dingle"), "Bucket"
            )
        )
        self.assertEqual(f.type, StorageError)


    @given(incidents(new=True), lists(incidentTypesText()))
    def test_setIncident_incidentTypes(
        self, incident: Incident, incidentTypes: Iterable[str]
    ) -> None:
        """
        :meth:`DataStore.setIncident_rangers` updates the ranger handles for
        the given incident in the data store.
        """
        self._test_setIncidentAttribute(
            incident, "setIncident_incidentTypes",
            "incidentTypes", incidentTypes,
        )


    def test_setIncident_incidentTypes_error(self) -> None:
        """
        :meth:`DataStore.setIncident_incidentTypes` raises :exc:`StorageError`
        when SQLite raises an exception.
        """
        event = Event(id="foo")
        store = self.store()
        self.successResultOf(store.createEvent(event))
        incident = self.successResultOf(store.createIncident(
            Incident(
                event=Event("foo"),
                number=0,
                created=DateTime.now(TimeZone.utc),
                state=IncidentState.new, priority=IncidentPriority.normal,
                summary="A thing happened",
                location=Location(name="There", address=None),
                rangerHandles=(), incidentTypes=(), reportEntries=(),
            ),
            "Hubcap")
        )
        store.bringThePain()

        f = self.failureResultOf(
            store.setIncident_incidentTypes(
                event, incident.number, ("Fun", "Boring"), "Bucket"
            )
        )
        self.assertEqual(f.type, StorageError)


    @given(
        incidents(new=True), frozensets(reportEntries(automatic=False)),
        rangerHandles(),
    )
    def test_addReportEntriesToIncident(
        self, incident: Incident, reportEntries: FrozenSet[ReportEntry],
        author: str
    ) -> None:
        """
        :meth:`DataStore.addReportEntriesToIncident` adds the given report
        entries to the given incident in the data store.
        """
        # Change author in report entries to match the author so we will use to
        # add them
        reportEntries = frozenset(
            r.replace(author=author) for r in reportEntries
        )

        # Store test data
        store = self.store()
        self.successResultOf(store.createEvent(incident.event))
        self.storeIncident(store, incident)

        # Fetch incident back so we're looking at the version from the DB
        incident = self.successResultOf(
            store.incidentWithNumber(incident.event, incident.number)
        )
        originalEntries = frozenset(incident.reportEntries)

        # Add report entries
        self.successResultOf(
            store.addReportEntriesToIncident(
                incident.event, incident.number, reportEntries, author
            )
        )

        # Get the updated incident with the new report entries
        updated = self.successResultOf(
            store.incidentWithNumber(incident.event, incident.number)
        )
        updatedEntries = frozenset(updated.reportEntries)

        # Updated entries minus the original entries == the added entries
        updatedNewEntries = updatedEntries - originalEntries
        self.assertTrue(
            reportEntriesEqualish(
                sorted(updatedNewEntries), sorted(reportEntries)
            )
        )


    def test_addReportEntriesToIncident_wrongAuthor(self) -> None:
        """
        :meth:`DataStore.addReportEntriesToIncident` raises :exc:`ValueError`
        when given report entries with an author that does not match the author
        that is adding the entries.
        """
        event = Event(id="foo")
        store = self.store()
        self.successResultOf(store.createEvent(event))
        incident = self.successResultOf(store.createIncident(
            Incident(
                event=Event("foo"),
                number=0,
                created=DateTime.now(TimeZone.utc),
                state=IncidentState.new, priority=IncidentPriority.normal,
                summary="A thing happened",
                location=Location(name="There", address=None),
                rangerHandles=(), incidentTypes=(), reportEntries=(),
            ),
            "Hubcap")
        )

        reportEntry = ReportEntry(
            created=DateTime.now(TimeZone.utc),
            author="Hubcap",
            automatic=False,
            text="Hello",
        )

        f = self.failureResultOf(
            store.addReportEntriesToIncident(
                event, incident.number, (reportEntry,), "Bucket"
            )
        )
        self.assertEqual(f.type, ValueError)


    def test_addReportEntriesToIncident_error(self) -> None:
        """
        :meth:`DataStore.addReportEntriesToIncident` raises :exc:`ValueError`
        when given report entries with an author that does not match the author
        that is adding the entries.
        """
        event = Event(id="foo")
        store = self.store()
        self.successResultOf(store.createEvent(event))
        incident = self.successResultOf(store.createIncident(
            Incident(
                event=Event("foo"),
                number=0,
                created=DateTime.now(TimeZone.utc),
                state=IncidentState.new, priority=IncidentPriority.normal,
                summary="A thing happened",
                location=Location(name="There", address=None),
                rangerHandles=(), incidentTypes=(), reportEntries=(),
            ),
            "Hubcap")
        )
        store.bringThePain()

        reportEntry = ReportEntry(
            created=DateTime.now(TimeZone.utc),
            author="Bucket",
            automatic=False,
            text="Hello",
        )

        f = self.failureResultOf(
            store.addReportEntriesToIncident(
                event, incident.number, (reportEntry,), "Bucket"
            )
        )
        self.assertEqual(f.type, StorageError)


    def assertIncidentsEqual(
        self, incidentA: Incident, incidentB: Incident,
        ignoreAutomatic: bool = False,
    ) -> None:
        if incidentA != incidentB:
            messages = []

            for attribute in attrFields(Incident):
                name = attribute.name
                valueA = getattr(incidentA, name)
                valueB = getattr(incidentB, name)

                if name == "created":
                    if dateTimesEqualish(valueA, valueB):
                        continue
                    else:
                        messages.append(
                            "{name} delta: {delta}"
                            .format(name=name, delta=valueA - valueB)
                        )
                elif name == "reportEntries":
                    if reportEntriesEqualish(valueA, valueB, ignoreAutomatic):
                        continue

                if valueA != valueB:
                    messages.append(
                        "{name} {valueA!r} != {valueB!r}"
                        .format(name=name, valueA=valueA, valueB=valueB)
                    )

            if messages:
                self.fail("Incidents do not match:\n" + "\n".join(messages))
