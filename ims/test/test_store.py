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
Tests for L{ims.store}.
"""

from datetime import datetime as DateTime

import twisted.trial.unittest
from twisted.python.filepath import FilePath

from ..tz import utc
from ims.json import incident_from_json, json_from_text
from ims.data import IncidentState, Incident, ReportEntry, Location
from ims.store import (
    StorageError, ReadOnlyStorage, Storage, NoSuchIncidentError
)



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
                for incident in data(rw_store):
                    rw_store.write_incident(incident)

        store = ReadOnlyStorage(fp)

        # Make sure provisioning is correct
        assert bool(store.path.exists()) == bool(provisioned)

        return store


    def test_read_raw(self):
        """
        L{ReadOnlyStorage.read_incident_with_number_raw} returns JSON text for
        the incident with the given number.
        """
        store = self.storage(data=test_incidents)
        for number in test_incident_etags:
            jsonText = store.read_incident_with_number_raw(number)
            json = json_from_text(jsonText)
            incident = incident_from_json(json, number=number)
            self.assertEquals(incident.number, number)


    def test_read_raw_not_found(self):
        """
        L{ReadOnlyStorage.read_incident_with_number_raw} raises
        L{NoSuchIncidentError} if there is no incident with the given number.
        """
        store = self.storage(provisioned=False)
        self.assertRaises(
            NoSuchIncidentError,
            store.read_incident_with_number_raw, 1
        )


    def test_read(self):
        """
        L{ReadOnlyStorage.read_incident_with_number} returns the incident with
        the given number.
        """
        store = self.storage(data=test_incidents)
        for number in test_incident_etags:
            incident = store.read_incident_with_number(number)
            self.assertEquals(incident.number, number)


    def test_read_not_found(self):
        """
        L{ReadOnlyStorage.read_incident_with_number} raises
        L{NoSuchIncidentError} if there is no incident with the given number.
        """
        store = self.storage(provisioned=False)
        self.assertRaises(
            NoSuchIncidentError,
            store.read_incident_with_number, 1
        )


    def test_etag(self):
        """
        L{ReadOnlyStorage.etag_for_incident_with_number} returns the ETag for
        the incident with the given number.
        """
        store = self.storage(data=test_incidents)
        for number, etag in test_incident_etags.iteritems():
            self.assertEquals(
                etag, store.etag_for_incident_with_number(number)
            )


    def test_list_new(self):
        """
        L{ReadOnlyStorage.list_incidents} returns no results for an
        unprovisioned store.
        """
        store = self.storage(provisioned=False)
        self.assertEquals(set(store.list_incidents()), set())


    def test_list_empty(self):
        """
        L{ReadOnlyStorage.list_incidents} returns no results for a provisioned
        but empty store.
        """
        store = self.storage()
        self.assertEquals(set(store.list_incidents()), set())


    def test_list_with_data_numbers(self):
        """
        L{ReadOnlyStorage.list_incidents} returns the correct numbers for a
        store with data.
        """
        store = self.storage(data=test_incidents)
        self.assertEquals(
            set(number for number, etag in store.list_incidents()),
            set(test_incident_etags.iterkeys())
        )


    def test_list_with_data_etags(self):
        """
        L{ReadOnlyStorage.list_incidents} returns the correct ETags for a
        store with data.
        """
        store = self.storage(data=test_incidents)
        self.assertEquals(
            set(etag for number, etag in store.list_incidents()),
            set(test_incident_etags.itervalues())
        )


    def test_max_new(self):
        """
        L{ReadOnlyStorage._max_incident_number} is C{0} for an unprovisioned
        store.
        """
        store = self.storage(provisioned=False)
        self.assertEquals(store._max_incident_number, 0)


    def test_max_empty(self):
        """
        L{ReadOnlyStorage._max_incident_number} is C{0} for an empty store.
        """
        store = self.storage()
        self.assertEquals(store._max_incident_number, 0)


    def test_max_with_data(self):
        """
        L{ReadOnlyStorage._max_incident_number} reflects the highest incident
        number in a store with data.
        """
        store = self.storage(data=test_incidents)
        self.assertEquals(store._max_incident_number, len(test_incident_etags))


    def test_max_set(self):
        """
        Setting L{ReadOnlyStorage._max_incident_number} and then getting it
        gives you the same value.
        """
        store = self.storage(provisioned=False)
        store._max_incident_number = 10
        self.assertEquals(store._max_incident_number, 10)


    def test_max_set_less_than(self):
        """
        Setting L{ReadOnlyStorage._max_incident_number} to a value lower than
        the current value raises an AssertionError.
        """
        store = self.storage(provisioned=False)
        store._max_incident_number = 10
        self.assertRaises(
            AssertionError,
            setattr, store, "_max_incident_number", 5
        )
        self.assertEquals(store._max_incident_number, 10)


    def test_locations(self):
        """
        L{ReadOnlyStorage.locations} yields all locations.
        """
        store = self.storage(data=test_incidents)
        self.assertEquals(
            set(store.locations()),
            set((
                Location(u"Ranger HQ", u"Esplanade & 5:45"),
                Location(u"Ranger HQ", u"Rod's Road & 2:00"),
                Location(u"Ranger Outpost Tokyo", u"9:00 & C"),
            ))
        )

    def test_search_no_terms(self):
        """
        Search with no terms yields all open incidents.
        """
        store = self.storage(data=test_incidents)
        self.assertEquals(
            set(store.search_incidents()),
            set(list_incidents((1, 2, 3)))
        )


    def test_search_with_terms(self):
        """
        Search with terms yields matching open incidents.
        """
        store = self.storage(data=test_incidents)
        self.assertEquals(
            set(store.search_incidents("overboard")),
            set(list_incidents((1,)))
        )


    def test_search_closed(self):
        """
        Search with C{closed=True} yields all incidents.
        """
        store = self.storage(data=test_incidents)

        self.assertEquals(
            set(store.search_incidents(show_closed=True)),
            set(list_incidents())
        )


    def test_search_since_until(self):
        """
        Search with C{since} and/or C{until} values yields time-bound
        incidents.
        """
        store = self.storage(data=test_incidents)

        self.assertEquals(
            set(store.search_incidents(since=time1)),
            set(list_incidents((1, 2, 3)))
        )

        self.assertEquals(
            set(store.search_incidents(since=time2)),
            set(list_incidents((1, 2, 3)))
        )

        self.assertEquals(
            set(store.search_incidents(since=time3)),
            set(list_incidents((2,)))
        )

        self.assertEquals(
            set(store.search_incidents(until=time1)),
            set(list_incidents((1,)))
        )

        self.assertEquals(
            set(store.search_incidents(until=time2)),
            set(list_incidents((1, 3)))
        )

        self.assertEquals(
            set(store.search_incidents(until=time3)),
            set(list_incidents((1, 2, 3)))
        )

        self.assertEquals(
            set(store.search_incidents(since=time1, until=time3)),
            set(list_incidents((1, 2, 3)))
        )

        self.assertEquals(
            set(store.search_incidents(since=time1, until=time2)),
            set(list_incidents((1, 3)))
        )

        self.assertEquals(
            set(store.search_incidents(since=time1, until=time1)),
            set(list_incidents((1,)))
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
                    store.write_incident(incident)

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


    def test_write_incident_new(self):
        """
        L{Storage.write_incident} on an unprovisioned store stores an incident.
        """
        store = self.storage(provisioned=False)
        incidents = frozenset(test_incidents(store))

        for incident in incidents:
            store.write_incident(incident)
            self.assertEquals(
                incident, store.read_incident_with_number(incident.number)
            )


    def test_next(self):
        """
        L{Storage.next_incident_number} returns the next available number.
        """
        store = self.storage(provisioned=False)
        last = store._max_incident_number
        next = store.next_incident_number()
        self.assertEquals(next, last + 1)
        self.assertRaises(
            NoSuchIncidentError,
            store.read_incident_with_number_raw, next
        )



# This is a function just to ensure that the test data aren't mutated.
def test_incidents(store):
    # Need to include time stamps below or etags will vary.
    return (
        Incident(
            number=store.next_incident_number(),
            rangers=(), incident_types=(), priority=5,
            report_entries=(
                ReportEntry(u"Tool", u"Man overboard!", time1),
                ReportEntry(u"Splinter", u"What?", time2),
            ),
            location=Location(u"Ranger Outpost Tokyo", u"9:00 & C"),
        ),
        Incident(
            number=store.next_incident_number(),
            rangers=(), incident_types=(), priority=5,
            report_entries=(
                ReportEntry(u"El Weso", u"Does this work?", time3),
            ),
            location=Location(u"Ranger HQ", u"Esplanade & 5:45"),
        ),
        Incident(
            number=store.next_incident_number(),
            rangers=(), incident_types=(), priority=5,
            report_entries=(
                ReportEntry(u"Librarian", u"Go read something.", time2),
            ),
            location=Location(u"Ranger HQ", u"Rod's Road & 2:00"),
        ),
        Incident(
            number=store.next_incident_number(),
            rangers=(), incident_types=(), priority=5,
            report_entries=(
                ReportEntry(u"da Mongolian", u"Fire!", time2),
            ),
            created=time1, state=IncidentState.closed,
        ),
    )


test_incident_etags = {
    1: "333c3d4175de688886a6e5de91becf2b63782403",
    2: "1e0fde2d8f7f6b61d8543e9ca28afa7e71f81f78",
    3: "8cbb368f5fc3091aa6a3d1eacfb687b6f695c881",
    4: "a1bfe51a1fb342c256f710896bb160875aa73460",
}


def list_incidents(numbers=test_incident_etags):
    return ((i, test_incident_etags[i]) for i in numbers)


time1 = DateTime(2012, 9, 1, 21, 0, tzinfo=utc)
time2 = DateTime(2013, 8, 31, 21, 0, tzinfo=utc)
time3 = DateTime(2014, 8, 23, 21, 0, tzinfo=utc)
