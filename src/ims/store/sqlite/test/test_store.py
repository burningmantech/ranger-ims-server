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
from datetime import datetime as DateTime, timedelta as TimeDelta
from io import StringIO
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, Set, Tuple, Union, cast

from attr import fields as attrFields

from hypothesis import assume, given
from hypothesis.strategies import booleans, text, tuples

from ims.ext.sqlite import Connection, Cursor, SQLITE_MAX_INT
from ims.ext.trial import TestCase
from ims.model import (
    Event, Incident, IncidentPriority, IncidentState,
    Location, RodGarettAddress,
)
from ims.model.strategies import (
    concentricStreetIDs, concentricStreetNames, events,
    incidentPriorities, incidentStates, incidentSummaries, incidentTypesText,
    incidents, locationNames, radialHours, radialMinutes, rangerHandles,
)

from .._store import DataStore, asTimeStamp, incidentStateAsID, priorityAsID
from ..._exceptions import StorageError

Dict, Set  # silence linter


__all__ = ()



class DataStoreTests(TestCase):
    """
    Tests for :class:`DataStore`
    """

    builtInTypes = {"Admin", "Junk"}


    def store(self) -> DataStore:
        return DataStore(dbPath=Path(self.mktemp()))


    def test_loadSchema(self) -> None:
        """
        :meth:`DataStore.loadSchema` caches and returns the schema.
        """
        store = self.store()

        DataStore._schema = None  # Reset in case previously cached
        schema = store._loadSchema()
        self.assertIsInstance(schema, str)

        # Check that class and instance access are the same object
        self.assertIdentical(schema, store._schema)
        self.assertIdentical(schema, DataStore._schema)


    def test_printSchema(self) -> None:
        """
        :meth:`DataStore.printSchema` prints the expected schema.
        """
        out = StringIO()
        DataStore.printSchema(out)
        schemaInfo = out.getvalue()
        self.assertEqual(
            schemaInfo,
            dedent(
                """
                ACCESS_MODE:
                  0: ID(text) not null *1
                CONCENTRIC_STREET:
                  0: EVENT(integer) not null *1
                  1: ID(text) not null *2
                  2: NAME(text) not null
                EVENT:
                  0: ID(integer) not null *1
                  1: NAME(text) not null
                EVENT_ACCESS:
                  0: EVENT(integer) not null *1
                  1: EXPRESSION(text) not null *2
                  2: MODE(text) not null
                INCIDENT:
                  0: EVENT(integer) not null *1
                  1: NUMBER(integer) not null *2
                  2: VERSION(integer) not null
                  3: CREATED(real) not null
                  4: PRIORITY(integer) not null
                  5: STATE(text) not null
                  6: SUMMARY(text)
                  7: LOCATION_NAME(text)
                  8: LOCATION_CONCENTRIC(text)
                  9: LOCATION_RADIAL_HOUR(integer)
                  10: LOCATION_RADIAL_MINUTE(integer)
                  11: LOCATION_DESCRIPTION(text)
                INCIDENT_INCIDENT_REPORT:
                  0: EVENT(integer) not null *1
                  1: INCIDENT_NUMBER(integer) not null *2
                  2: INCIDENT_REPORT_NUMBER(integer) not null *3
                INCIDENT_REPORT:
                  0: NUMBER(integer) not null *1
                  1: CREATED(real) not null
                  2: SUMMARY(text)
                INCIDENT_REPORT__REPORT_ENTRY:
                  0: INCIDENT_REPORT_NUMBER(integer) not null *1
                  1: REPORT_ENTRY(integer) not null *2
                INCIDENT_STATE:
                  0: ID(text) not null *1
                INCIDENT_TYPE:
                  0: ID(integer) not null *1
                  1: NAME(text) not null
                  2: HIDDEN(numeric) not null
                INCIDENT__INCIDENT_TYPE:
                  0: EVENT(integer) not null *1
                  1: INCIDENT_NUMBER(integer) not null *2
                  2: INCIDENT_TYPE(integer) not null *3
                INCIDENT__RANGER:
                  0: EVENT(integer) not null *1
                  1: INCIDENT_NUMBER(integer) not null *2
                  2: RANGER_HANDLE(text) not null *3
                INCIDENT__REPORT_ENTRY:
                  0: EVENT(integer) not null *1
                  1: INCIDENT_NUMBER(integer) not null *2
                  2: REPORT_ENTRY(integer) not null *3
                REPORT_ENTRY:
                  0: ID(integer) not null *1
                  1: AUTHOR(text) not null
                  2: TEXT(text) not null
                  3: CREATED(real) not null
                  4: GENERATED(numeric) not null
                SCHEMA_INFO:
                  0: VERSION(integer) not null
                """[1:]
            )
        )


    def test_db(self) -> None:
        """
        :meth:`DataStore._db` returns a :class:`Connection`.
        """
        store = self.store()
        self.assertIsInstance(store._db, Connection)


    def test_events(self) -> None:
        """
        :meth:`DataStore.events` returns all events.
        """
        store = self.store()
        store._db.executescript(
            dedent(
                """
                insert into EVENT (NAME) values ('Event A');
                insert into EVENT (NAME) values ('Event B');
                """
            )
        )

        events = frozenset(self.successResultOf(store.events()))

        self.assertEqual(events, {Event("Event A"), Event("Event B")})


    @given(events())
    def test_createEvent(self, event: Event) -> None:
        """
        :meth:`DataStore.createEvent` creates the given event.
        """
        store = self.store()
        self.successResultOf(store.createEvent(event))
        stored = frozenset(self.successResultOf(store.events()))
        self.assertEqual(stored, frozenset((event,)))


    def test_createEvent_duplicate(self) -> None:
        """
        :meth:`DataStore.createEvent` raises :exc:`StorageError` when given an
        event that already exists in the data store.
        """
        event = Event(id="foo")
        store = self.store()
        self.successResultOf(store.createEvent(event))
        f = self.failureResultOf(store.createEvent(event))
        self.assertEqual(f.type, StorageError)


    @given(tuples(tuples(incidentTypesText(), booleans())))
    def test_incidentTypes(self, data: Tuple[Tuple[str, bool]]) -> None:
        """
        :meth:`DataStore.incidentTypes` returns visible incident types.
        """
        store = self.store()
        for (name, hidden) in data:
            assume(name not in self.builtInTypes)
            store._db.execute(
                "insert into INCIDENT_TYPE (NAME, HIDDEN) "
                "values (:name, :hidden)",
                dict(name=name, hidden=hidden)
            )

        incidentTypes = frozenset(
            self.successResultOf(store.incidentTypes())
        )
        expected = frozenset(
            (name for (name, hidden) in data if not hidden)
        ) | self.builtInTypes

        self.assertEqual(incidentTypes, expected)


    @given(tuples(tuples(incidentTypesText(), booleans())))
    def test_incidentTypes_includeHidden(
        self, data: Tuple[Tuple[str, bool]]
    ) -> None:
        """
        :meth:`DataStore.incidentTypes` if given CL{includeHidden=True} returns
        all incident types.
        """
        store = self.store()
        for (name, hidden) in data:
            assume(name not in self.builtInTypes)
            store._db.execute(
                "insert into INCIDENT_TYPE (NAME, HIDDEN) "
                "values (:name, :hidden)",
                dict(name=name, hidden=hidden)
            )

        incidentTypes = frozenset(
            self.successResultOf(store.incidentTypes(includeHidden=True))
        )
        expected = frozenset(
            (name for (name, hidden) in data)
        ) | self.builtInTypes

        self.assertEqual(incidentTypes, expected)


    @given(incidentTypesText(), booleans())
    def test_createIncidentType(self, incidentType: str, hidden: bool) -> None:
        """
        :meth:`DataStore.createIncidentType` creates the incident type.
        """
        assume(incidentType not in self.builtInTypes)

        store = self.store()
        self.successResultOf(
            store.createIncidentType(incidentType, hidden=hidden)
        )

        incidentTypes = frozenset(self.successResultOf(store.incidentTypes()))
        if hidden:
            self.assertNotIn(incidentType, incidentTypes)
        else:
            self.assertIn(incidentType, incidentTypes)

        incidentTypes = frozenset(
            self.successResultOf(store.incidentTypes(includeHidden=True))
        )
        self.assertIn(incidentType, incidentTypes)


    def test_createIncidentType_duplicate(self) -> None:
        """
        :meth:`DataStore.createIncidentType` raises :exc:`StorageError` when
        given an incident type that already exists in the data store.
        """
        incidentType = "foo"
        store = self.store()
        self.successResultOf(store.createIncidentType(incidentType))
        f = self.failureResultOf(store.createIncidentType(incidentType))
        self.assertEqual(f.type, StorageError)


    def test_showIncidentTypes(self) -> None:
        """
        :meth:`DataStore.showIncidentTypes` makes the given incident types
        visible.
        """
        incidentType = "foo"
        store = self.store()
        self.successResultOf(
            store.createIncidentType(incidentType, hidden=True)
        )
        self.assertNotIn(
            incidentType, self.successResultOf(store.incidentTypes())
        )
        self.successResultOf(store.showIncidentTypes((incidentType,)))
        self.assertIn(
            incidentType, self.successResultOf(store.incidentTypes())
        )
        # Again should also work
        self.successResultOf(store.showIncidentTypes((incidentType,)))
        self.assertIn(
            incidentType, self.successResultOf(store.incidentTypes())
        )


    def test_hideIncidentTypes(self) -> None:
        """
        :meth:`DataStore.showIncidentTypes` makes the given incident types
        hidden.
        """
        incidentType = "foo"
        store = self.store()
        self.successResultOf(
            store.createIncidentType(incidentType, hidden=False)
        )
        self.assertIn(
            incidentType, self.successResultOf(store.incidentTypes())
        )
        self.successResultOf(store.hideIncidentTypes((incidentType,)))
        self.assertNotIn(
            incidentType, self.successResultOf(store.incidentTypes())
        )
        # Again should also work
        self.successResultOf(store.hideIncidentTypes((incidentType,)))
        self.assertNotIn(
            incidentType, self.successResultOf(store.incidentTypes())
        )


    @given(events(), concentricStreetIDs(), concentricStreetNames())
    def test_concentricStreets(
        self, event: Event, streetID: str, streetName: str
    ) -> None:
        """
        :meth:`DataStore.createConcentricStreet` returns the concentric streets
        for the given event.
        """
        store = self.store()

        self.successResultOf(store.createEvent(event))

        self.storeConcentricStreet(store._db, event, streetID, streetName)

        concentricStreets = self.successResultOf(
            store.concentricStreets(event)
        )

        self.assertEqual(len(concentricStreets), 1)
        self.assertEqual(concentricStreets.get(streetID), streetName)


    @given(events(), concentricStreetIDs(), concentricStreetNames())
    def test_createConcentricStreet(
        self, event: Event, id: str, name: str
    ) -> None:
        """
        :meth:`DataStore.createConcentricStreet` creates a concentric streets
        for the given event.
        """
        store = self.store()

        self.successResultOf(store.createEvent(event))

        self.successResultOf(
            store.createConcentricStreet(event=event, id=id, name=name)
        )
        stored = self.successResultOf(store.concentricStreets(event=event))

        self.assertEqual(len(stored), 1)
        self.assertEqual(stored.get(id), name)


    @given(tuples(incidents()))
    def test_incidents(self, incidents: Tuple[Incident]) -> None:
        """
        :meth:`DataStore.incidents` returns all incidents.
        """
        events: Dict[Event, Dict[int, Incident]] = defaultdict(defaultdict)

        store = self.store()

        for incident in incidents:
            assume(incident.number <= SQLITE_MAX_INT)
            assume(incident.number not in events[incident.event])

            self.storeIncident(store, incident)

            events[incident.event][incident.number] = incident

        for event in events:
            for retrieved in self.successResultOf(
                store.incidents(event)
            ):
                self.assertIncidentsEqual(
                    retrieved, events[incident.event][retrieved.number]
                )


    @given(incidents())
    def test_incidentWithNumber(self, incident: Incident) -> None:
        """
        :meth:`DataStore.incidentWithNumber` return the specified incident.
        """
        assume(incident.number <= SQLITE_MAX_INT)

        store = self.store()

        self.storeIncident(store, incident)

        retrieved = self.successResultOf(
            store.incidentWithNumber(incident.event, incident.number)
        )

        self.assertIncidentsEqual(retrieved, incident)


    @given(incidents(new=True), rangerHandles())
    def test_createIncident(self, incident: Incident, author: str) -> None:
        """
        :meth:`DataStore.createIncident` creates the given incident.
        """
        store = self.store()

        self.successResultOf(store.createEvent(incident.event))

        for incidentType in incident.incidentTypes:
            self.successResultOf(store.createIncidentType(incidentType))

        address = incident.location.address
        if (
            isinstance(address, RodGarettAddress) and
            address.concentric is not None
        ):
            self.successResultOf(
                store.createConcentricStreet(
                    incident.event, address.concentric, "Sesame Street"
                )
            )

        # The returned incident should be the same, except for modified number
        returnedIncident = self.successResultOf(
            store.createIncident(incident=incident, author=author)
        )
        self.assertIncidentsEqual(
            returnedIncident.replace(number=0), incident, True
        )
        self.assertNotEqual(returnedIncident.number, 0)

        # Stored incidents should be contain only the returned incident above
        storedIncidents = tuple(
            self.successResultOf(store.incidents(event=incident.event))
        )
        self.assertEqual(len(storedIncidents), 1)
        self.assertIncidentsEqual(storedIncidents[0], returnedIncident)


    def _test_setIncidentAttribute(
        self, incident: Incident,
        methodName: str, attributeName: str, value: Any
    ) -> None:
        store = self.store()

        self.storeIncident(store, incident)

        setter = getattr(store, methodName)

        # For concentric streets, we need to make sure they exist first.
        if attributeName == "location.address.concentric":
            self.storeConcentricStreet(
                store._db, incident.event, value, "Concentric Street",
                ignoreDuplicates=True,
            )

        self.successResultOf(
            setter(incident.event, incident.number, value, "Hubcap")
        )

        retrieved = self.successResultOf(
            store.incidentWithNumber(incident.event, incident.number)
        )

        # Normalize location if we're updating the address.
        if attributeName.startswith("location.address."):
            incident = self.normalizeAddress(incident)

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

        self.assertIncidentsEqual(retrieved, incident, ignoreInitial=True)


    @given(incidents(new=True), incidentPriorities())
    def test_setIncidentPriority(
        self, incident: Incident, priority: IncidentPriority
    ) -> None:
        """
        :meth:`DataStore.setIncidentPriority` updates the priority for the
        incident with the given number in the data store.
        """
        self._test_setIncidentAttribute(
            incident, "setIncidentPriority", "priority", priority
        )


    @given(incidents(new=True), incidentStates())
    def test_setIncidentState(
        self, incident: Incident, state: IncidentState
    ) -> None:
        """
        :meth:`DataStore.setIncidentState` updates the state for the incident
        with the given number in the data store.
        """
        self._test_setIncidentAttribute(
            incident, "setIncidentState", "state", state
        )


    @given(incidents(new=True), incidentSummaries())
    def test_setIncidentSummary(
        self, incident: Incident, summary: str
    ) -> None:
        """
        :meth:`DataStore.setIncidentSummary` updates the summary for the
        incident with the given number in the data store.
        """
        self._test_setIncidentAttribute(
            incident, "setIncidentSummary", "summary", summary
        )


    @given(incidents(new=True), locationNames())
    def test_setIncidentLocationName(
        self, incident: Incident, name: str
    ) -> None:
        """
        :meth:`DataStore.setIncidentLocationName` updates the location name for
        the incident with the given number in the data store.
        """
        self._test_setIncidentAttribute(
            incident, "setIncidentLocationName", "location.name", name
        )


    @given(incidents(new=True), concentricStreetIDs())
    def test_setIncidentLocationConcentricStreet(
        self, incident: Incident, streetID: str
    ) -> None:
        """
        :meth:`DataStore.setIncidentLocationConcentricStreet` updates the
        location concentric street for the incident with the given number in
        the data store.
        """
        self._test_setIncidentAttribute(
            incident, "setIncidentLocationConcentricStreet",
            "location.address.concentric", streetID,
        )


    @given(incidents(new=True), radialHours())
    def test_setIncidentLocationRadialHour(
        self, incident: Incident, radialHour: int
    ) -> None:
        """
        :meth:`DataStore.setIncidentLocationRadialHour` updates the location
        radial hour for the incident with the given number in the data store.
        """
        self._test_setIncidentAttribute(
            incident, "setIncidentLocationRadialHour",
            "location.address.radialHour", radialHour,
        )


    @given(incidents(new=True), radialMinutes())
    def test_setIncidentLocationRadialMinute(
        self, incident: Incident, radialMinute: int
    ) -> None:
        """
        :meth:`DataStore.setIncidentLocationRadialMinute` updates the location
        radial minute for the incident with the given number in the data store.
        """
        self._test_setIncidentAttribute(
            incident, "setIncidentLocationRadialMinute",
            "location.address.radialMinute", radialMinute,
        )


    @given(incidents(new=True), text())
    def test_setIncidentLocationDescription(
        self, incident: Incident, description: str
    ) -> None:
        """
        :meth:`DataStore.setIncidentLocationDescription` updates the location
        description for the incident with the given number in the data store.
        """
        self._test_setIncidentAttribute(
            incident, "setIncidentLocationDescription",
            "location.address.description", description,
        )


    def assertIncidentsEqual(
        self, incidentA: Incident, incidentB: Incident,
        ignoreInitial: bool = False,
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

                if name == "reportEntries":
                    if ignoreInitial:
                        # Remove automatic entries
                        _valueA = tuple(e for e in valueA if not e.automatic)

                        if _valueA == valueA:
                            self.fail("No initial report entries found.")

                        valueA = _valueA

                    if len(valueA) == len(valueB):
                        for entryA, entryB in zip(valueA, valueB):
                            if entryA != entryB:
                                if entryA.author != entryB.author:
                                    break
                                if entryA.automatic != entryB.automatic:
                                    break
                                if entryA.text != entryB.text:
                                    break
                                if not dateTimesEqualish(
                                    entryA.created, entryB.created
                                ):
                                    break
                        else:
                            continue

                if valueA != valueB:
                    messages.append(
                        "{name} {valueA!r} != {valueB!r}"
                        .format(name=name, valueA=valueA, valueB=valueB)
                    )

            if messages:
                self.fail("Incidents do not match:\n" + "\n".join(messages))


    # FIXME: A better plan here would be to create a mock DB object that yields
    # the expected rows, instead of writing to an actual DB.
    # Since it's SQLite, which isn't actually async, that's not a huge deal,
    # except there's a lot of fragile code below.

    def storeConcentricStreet(
        self, cursor: Union[Connection, Cursor], event: Event, streetID: str,
        streetName: str, ignoreDuplicates: bool = False,
    ) -> None:
        if ignoreDuplicates:
            ignore = " or ignore"
        else:
            ignore = ""

        cursor.execute(
            dedent(
                """
                insert{ignore} into CONCENTRIC_STREET (EVENT, ID, NAME)
                values (
                    (select ID from EVENT where NAME = :eventID),
                    :streetID,
                    :streetName
                )
                """.format(ignore=ignore)
            ),
            dict(
                eventID=event.id, streetID=streetID, streetName=streetName
            )
        )


    def normalizeAddress(self, incident: Incident) -> Incident:
        # Normalize address to Rod Garett; DB schema only supports those.
        address = incident.location.address
        if address is not None and not isinstance(address, RodGarettAddress):
            incident = incident.replace(
                location=Location(
                    name=incident.location.name,
                    address=RodGarettAddress(
                        description=address.description,
                    )
                )
            )
        return incident


    def storeIncident(self, store: DataStore, incident: Incident) -> None:
        with store._db as db:
            cursor = db.cursor()
            try:
                self._storeIncident(cursor, incident)
            finally:
                cursor.close()


    def _storeIncident(self, cursor: Cursor, incident: Incident) -> None:
        incident = self.normalizeAddress(incident)

        location = incident.location
        address = cast(RodGarettAddress, location.address)

        cursor.execute(
            "insert into EVENT (NAME) values (:eventID);",
            dict(eventID=incident.event.id)
        )

        if address.concentric is not None:
            self.storeConcentricStreet(
                cursor, incident.event, address.concentric, "Some Street"
            )

        cursor.execute(
            dedent(
                """
                insert into INCIDENT (
                    EVENT, NUMBER, VERSION, CREATED, PRIORITY, STATE, SUMMARY,
                    LOCATION_NAME,
                    LOCATION_CONCENTRIC,
                    LOCATION_RADIAL_HOUR,
                    LOCATION_RADIAL_MINUTE,
                    LOCATION_DESCRIPTION
                ) values (
                    (select ID from EVENT where NAME = :eventID),
                    :incidentNumber,
                    1,
                    :incidentCreated,
                    :incidentPriority,
                    :incidentState,
                    :incidentSummary,
                    :locationName,
                    :locationConcentric,
                    :locationRadialHour,
                    :locationRadialMinute,
                    :locationDescription
                )
                """
            ),
            dict(
                eventID=incident.event.id,
                incidentCreated=asTimeStamp(incident.created),
                incidentNumber=incident.number,
                incidentSummary=incident.summary,
                incidentPriority=priorityAsID(incident.priority),
                incidentState=incidentStateAsID(incident.state),
                locationName=location.name,
                locationConcentric=address.concentric,
                locationRadialHour=address.radialHour,
                locationRadialMinute=address.radialMinute,
                locationDescription=address.description,
            )
        )

        for rangerHandle in incident.rangerHandles:
            cursor.execute(
                dedent(
                    """
                    insert into INCIDENT__RANGER
                    (EVENT, INCIDENT_NUMBER, RANGER_HANDLE)
                    values (
                        (select ID from EVENT where NAME = :eventID),
                        :incidentNumber,
                        :rangerHandle
                    )
                    """
                ),
                dict(
                    eventID=incident.event.id,
                    incidentNumber=incident.number,
                    rangerHandle=rangerHandle
                )
            )

        for incidentType in incident.incidentTypes:
            cursor.execute(
                dedent(
                    """
                    insert into INCIDENT_TYPE (NAME, HIDDEN)
                    values (:incidentType, 0)
                    """
                ),
                dict(incidentType=incidentType)
            )
            cursor.execute(
                dedent(
                    """
                    insert into INCIDENT__INCIDENT_TYPE
                    (EVENT, INCIDENT_NUMBER, INCIDENT_TYPE)
                    values (
                        (select ID from EVENT where NAME = :eventID),
                        :incidentNumber,
                        (
                            select ID from INCIDENT_TYPE
                            where NAME = :incidentType
                        )
                    )
                    """
                ),
                dict(
                    eventID=incident.event.id,
                    incidentNumber=incident.number,
                    incidentType=incidentType
                )
            )

        for reportEntry in incident.reportEntries:
            cursor.execute(
                dedent(
                    """
                    insert into REPORT_ENTRY (AUTHOR, TEXT, CREATED, GENERATED)
                    values (:author, :text, :created, :automatic)
                    """
                ),
                dict(
                    created=asTimeStamp(reportEntry.created),
                    author=reportEntry.author,
                    automatic=reportEntry.automatic,
                    text=reportEntry.text,
                )
            )
            cursor.execute(
                dedent(
                    """
                    insert into INCIDENT__REPORT_ENTRY (
                        EVENT, INCIDENT_NUMBER, REPORT_ENTRY
                    )
                    values (
                        (select ID from EVENT where NAME = :eventID),
                        :incidentNumber,
                        :reportEntryID
                    )
                    """
                ),
                dict(
                    eventID=incident.event.id,
                    incidentNumber=incident.number,
                    reportEntryID=cursor.lastrowid
                )
            )



def dateTimesEqualish(a: DateTime, b: DateTime) -> bool:
    """
    Compare two :class:`DateTimes`.
    Because floating point math, apply some "close enough" logic.
    """
    return a - b < TimeDelta(microseconds=20)
