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
Tests for L{ims.store.file}.
"""

__all__ = []

from datetime import datetime as DateTime

import twisted.trial.unittest
from twisted.python.filepath import FilePath

from ...tz import utc
from ...data.model import IncidentState, Incident, ReportEntry
from ...data.json import (
    incidentFromJSON, incidentAsJSON, objectFromJSONText, jsonTextFromObject
)
from ...data.test.test_model import (
    location_tokyo, location_man, location_zero
)
from ..istore import StorageError, NoSuchIncidentError
from .._file import Storage, ReadOnlyStorage, etag_hash



class ReadOnlyStorageTests(twisted.trial.unittest.TestCase):
    """
    Tests for L{ims.store.ReadOnlyStorage}
    """

    def storage(self, provisioned=True, data=None):
        fp = FilePath(self.mktemp())

        if provisioned:
            rw_store = Storage(fp)
            rw_store.provision()

            if data is not None:
                for incident in data():
                    # Make sure that the incident numbers vended by
                    # data() match the nextIncidentNumber()
                    # implementation.
                    assert incident.number == rw_store.nextIncidentNumber()
                    rw_store.writeIncident(incident)

        store = ReadOnlyStorage(fp)

        # Make sure provisioning is correct
        assert bool(store.path.exists()) == bool(provisioned)

        return store


    def storageWithSourceData(self, source):
        fp = FilePath(self.mktemp())

        rw_store = Storage(fp)
        rw_store.provision()

        # Write out some test data.
        number = 0
        for text in source:
            number += 1
            rw_store._writeIncidentText(number, text)

        return ReadOnlyStorage(fp)


    def test_read_raw(self):
        """
        L{ReadOnlyStorage.readIncidentWithNumberRaw} returns JSON text for
        the incident with the given number.
        """
        store = self.storage(data=test_incidents)
        for number in test_incident_etags:
            jsonText = store.readIncidentWithNumberRaw(number)
            json = objectFromJSONText(jsonText)
            incident = incidentFromJSON(json, number=number)
            self.assertEquals(incident.number, number)


    def test_read_raw_not_found(self):
        """
        L{ReadOnlyStorage.readIncidentWithNumberRaw} raises
        L{NoSuchIncidentError} if there is no incident with the given number.
        """
        store = self.storage(provisioned=False)
        self.assertRaises(
            NoSuchIncidentError,
            store.readIncidentWithNumberRaw, 1
        )


    def test_read(self):
        """
        L{ReadOnlyStorage.readIncidentWithNumber} returns the incident with
        the given number.
        """
        store = self.storage(data=test_incidents)
        for number in test_incident_etags:
            incident = store.readIncidentWithNumber(number)
            self.assertEquals(incident.number, number)


    def test_read_not_found(self):
        """
        L{ReadOnlyStorage.readIncidentWithNumber} raises
        L{NoSuchIncidentError} if there is no incident with the given number.
        """
        store = self.storage(provisioned=False)
        self.assertRaises(
            NoSuchIncidentError,
            store.readIncidentWithNumber, 1
        )


    def test_read_2014_reportEntry_createdNoneUseFirstReportEntry(self):
        """
        2014 data has report entries with no created timestamp because bugs.
        C{:-(}
        """
        source = [
            """
            {
                "number": 1,
                "priority": 1,
                "report_entries": [
                    {
                        "author": "Tool",
                        "text": "Hi!",
                        "created": "2012-09-01T21:00:00Z"
                    }
                ]
            }
            """
        ]

        store = self.storageWithSourceData(source)

        for number, etag in store.listIncidents():
            incident = store.readIncidentWithNumber(number)
            self.assertEquals(incident.created, time1)


    def test_read_2014_reportEntry_authorNone(self):
        """
        2014 data has report entries with no author because bugs.  C{:-(}
        """
        source = [
            """
            {
                "number": 1, "priority": 1,
                "timestamp": "2014-08-30T21:38:11Z",
                "report_entries": [
                    {
                        "text": "Hi!",
                        "created": "2014-08-23T21:19:00Z"
                    }
                ]
            }
            """
        ]

        store = self.storageWithSourceData(source)

        for number, etag in store.listIncidents():
            incident = store.readIncidentWithNumber(number)
            for entry in incident.reportEntries:
                self.assertEquals(entry.author, "<unknown>")


    def test_etag(self):
        """
        L{ReadOnlyStorage.etagForIncidentWithNumber} returns the ETag for
        the incident with the given number.
        """
        store = self.storage(data=test_incidents)
        for number, etag in test_incident_etags.iteritems():
            self.assertEquals(
                etag, store.etagForIncidentWithNumber(number)
            )


    def test_list_new(self):
        """
        L{ReadOnlyStorage.listIncidents} returns no results for an
        unprovisioned store.
        """
        store = self.storage(provisioned=False)
        self.assertEquals(set(store.listIncidents()), set())


    def test_list_empty(self):
        """
        L{ReadOnlyStorage.listIncidents} returns no results for a provisioned
        but empty store.
        """
        store = self.storage()
        self.assertEquals(set(store.listIncidents()), set())


    def test_list_with_data_numbers(self):
        """
        L{ReadOnlyStorage.listIncidents} returns the correct numbers for a
        store with data.
        """
        store = self.storage(data=test_incidents)
        self.assertEquals(
            set(number for number, etag in store.listIncidents()),
            set(test_incident_etags.iterkeys())
        )


    def test_list_with_data_etags(self):
        """
        L{ReadOnlyStorage.listIncidents} returns the correct ETags for a
        store with data.
        """
        store = self.storage(data=test_incidents)
        self.assertEquals(
            set(etag for number, etag in store.listIncidents()),
            set(test_incident_etags.itervalues())
        )


    def test_max_new(self):
        """
        L{ReadOnlyStorage._maxIncidentNumber} is C{0} for an unprovisioned
        store.
        """
        store = self.storage(provisioned=False)
        self.assertEquals(store._maxIncidentNumber, 0)


    def test_max_empty(self):
        """
        L{ReadOnlyStorage._maxIncidentNumber} is C{0} for an empty store.
        """
        store = self.storage()
        self.assertEquals(store._maxIncidentNumber, 0)


    def test_max_with_data(self):
        """
        L{ReadOnlyStorage._maxIncidentNumber} reflects the highest incident
        number in a store with data.
        """
        store = self.storage(data=test_incidents)
        self.assertEquals(store._maxIncidentNumber, len(test_incident_etags))


    def test_max_set(self):
        """
        Setting L{ReadOnlyStorage._maxIncidentNumber} and then getting it
        gives you the same value.
        """
        store = self.storage(provisioned=False)
        store._maxIncidentNumber = 10
        self.assertEquals(store._maxIncidentNumber, 10)


    def test_max_set_less_than(self):
        """
        Setting L{ReadOnlyStorage._maxIncidentNumber} to a value lower than
        the current value raises an AssertionError.
        """
        store = self.storage(provisioned=False)
        store._maxIncidentNumber = 10
        self.assertRaises(
            AssertionError,
            setattr, store, "_maxIncidentNumber", 5
        )
        self.assertEquals(store._maxIncidentNumber, 10)


    def test_locations(self):
        """
        L{ReadOnlyStorage.locations} yields all locations.
        """
        store = self.storage(data=test_incidents)
        self.assertEquals(
            set(store.locations()),
            set((location_tokyo, location_man, location_zero)),
        )

    def test_search_no_terms(self):
        """
        Search with no terms yields all open incidents.
        """
        store = self.storage(data=test_incidents)
        self.assertEquals(
            set(store.searchIncidents()),
            set(listIncidents((1, 2, 3)))
        )


    def test_search_with_terms(self):
        """
        Search with terms yields matching open incidents.
        """
        store = self.storage(data=test_incidents)
        self.assertEquals(
            set(store.searchIncidents("overboard")),
            set(listIncidents((1,)))
        )


    def test_search_closed(self):
        """
        Search with C{closed=True} yields all incidents.
        """
        store = self.storage(data=test_incidents)

        self.assertEquals(
            set(store.searchIncidents(showClosed=True)),
            set(listIncidents())
        )


    def test_search_since_until(self):
        """
        Search with C{since} and/or C{until} values yields time-bound
        incidents.
        """
        store = self.storage(data=test_incidents)

        self.assertEquals(
            set(store.searchIncidents(since=time1)),
            set(listIncidents((1, 2, 3)))
        )

        self.assertEquals(
            set(store.searchIncidents(since=time2)),
            set(listIncidents((1, 2, 3)))
        )

        self.assertEquals(
            set(store.searchIncidents(since=time3)),
            set(listIncidents((2,)))
        )

        self.assertEquals(
            set(store.searchIncidents(until=time1)),
            set(listIncidents((1,)))
        )

        self.assertEquals(
            set(store.searchIncidents(until=time2)),
            set(listIncidents((1, 3)))
        )

        self.assertEquals(
            set(store.searchIncidents(until=time3)),
            set(listIncidents((1, 2, 3)))
        )

        self.assertEquals(
            set(store.searchIncidents(since=time1, until=time3)),
            set(listIncidents((1, 2, 3)))
        )

        self.assertEquals(
            set(store.searchIncidents(since=time1, until=time2)),
            set(listIncidents((1, 3)))
        )

        self.assertEquals(
            set(store.searchIncidents(since=time1, until=time1)),
            set(listIncidents((1,)))
        )



class StorageTests(twisted.trial.unittest.TestCase):
    """
    Tests for L{ims.store.Storage}
    """

    def storage(self, provisioned=True, data=None, fp=None):
        if fp is None:
            fp = FilePath(self.mktemp())

        store = Storage(fp)

        if provisioned:
            store.provision()

            if data is not None:
                for incident in data(store):
                    # Make sure that the incident numbers vended by data()
                    # match the nextIncidentNumber() implementation.
                    assert incident.number == store.nextIncidentNumber()
                    store.writeIncident(incident)

        # Make sure provisioning is correct
        assert bool(store.path.exists()) == bool(provisioned)

        return store


    def test_provision_new(self):
        """
        Calling L{Storage.provision} on a non-existing store creates it.
        """
        store = self.storage(provisioned=False)
        store.provision()
        self.assertTrue(store.path.isdir())


    def test_provision_exists(self):
        """
        Calling L{Storage.provision} again is harmless.
        """
        store = self.storage()
        store.provision()
        self.assertTrue(store.path.isdir())


    def test_provision_conflicting_file(self):
        """
        Calling L{Storage.provision} when there is a file in the way raises
        L{StorageError}.
        """
        fp = FilePath(self.mktemp())
        store = self.storage(provisioned=False, fp=fp)
        fp.setContent(b"")
        self.assertRaises(StorageError, store.provision)


    def test_writeIncident_new(self):
        """
        L{Storage.writeIncident} on an unprovisioned store stores an incident.
        """
        store = self.storage(provisioned=False)
        incidents = frozenset(test_incidents())

        for incident in incidents:
            # Make sure that the incident numbers vended by data()
            # match the nextIncidentNumber() implementation.
            assert incident.number == store.nextIncidentNumber()
            store.writeIncident(incident)
            self.assertEquals(
                incident, store.readIncidentWithNumber(incident.number)
            )


    def test_next(self):
        """
        L{Storage.nextIncidentNumber} returns the next available number.
        """
        store = self.storage(provisioned=False)
        last = store._maxIncidentNumber
        next = store.nextIncidentNumber()
        self.assertEquals(next, last + 1)
        self.assertRaises(
            NoSuchIncidentError,
            store.readIncidentWithNumberRaw, next
        )



time1 = DateTime(2012, 9, 1, 21, 0, 0, tzinfo=utc)
time2 = DateTime(2013, 8, 31, 21, 0, 0, tzinfo=utc)
time3 = DateTime(2014, 8, 23, 21, 0, 0, tzinfo=utc)


# This is a function just to ensure that the test data aren't mutated.
def test_incidents():
    # Need to include time stamps below or etags will vary.

    def next_number():
        number_container[0] += 1
        return number_container[0]
    number_container = [0]

    incidents = (
        Incident(
            number=next_number(),
            rangers=(), incidentTypes=(), priority=5,
            created=time1,
            reportEntries=(
                ReportEntry("Tool", "Man overboard!", time1),
                ReportEntry("Splinter", "What?", time2),
            ),
            location=location_tokyo,
        ),
        Incident(
            number=next_number(),
            rangers=(), incidentTypes=(), priority=5,
            created=time3,
            reportEntries=(
                ReportEntry("El Weso", "Does this work?", time3),
            ),
            location=location_zero,
        ),
        Incident(
            number=next_number(),
            rangers=(), incidentTypes=(), priority=5,
            created=time2,
            reportEntries=(
                ReportEntry("Librarian", "Go read something.", time2),
            ),
            location=location_man,
        ),
        Incident(
            number=next_number(),
            rangers=(), incidentTypes=(), priority=5,
            created=time1, state=IncidentState.closed,
            reportEntries=(
                ReportEntry("da Mongolian", "Fire!", time2),
            ),
        ),
    )

    return incidents


def expectedETagForIncident(incident):
    json = incidentAsJSON(incident)
    text = jsonTextFromObject(json)

    return etag_hash(text).hexdigest()


test_incident_etags = dict((
    (incident.number, expectedETagForIncident(incident))
    for incident in test_incidents()
))


def listIncidents(numbers=test_incident_etags):
    return ((i, test_incident_etags[i]) for i in numbers)
