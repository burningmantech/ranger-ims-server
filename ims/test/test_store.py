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
from ims.data import IncidentState, Incident, ReportEntry
from ims.store import (
    StorageError, ReadOnlyStorage, Storage, NoSuchIncidentError
)
from .test_data import location_tokyo, location_man, location_zero



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
                    # Make sure that the incident numbers vended by data()
                    # match the next_incident_number() implementation.
                    assert incident.number == rw_store.next_incident_number()
                    rw_store.write_incident(incident)

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
            rw_store._write_incident_text(number, text)

        return ReadOnlyStorage(fp)


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
                        "created":"2012-09-01T21:00:00Z"
                    }
                ]
            }
            """
        ]

        store = self.storageWithSourceData(source)

        for number, etag in store.list_incidents():
            incident = store.read_incident_with_number(number)
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
                        "created":"2014-08-23T21:19:00Z"
                    }
                ]
            }
            """
        ]

        store = self.storageWithSourceData(source)

        for number, etag in store.list_incidents():
            incident = store.read_incident_with_number(number)
            for entry in incident.report_entries:
                self.assertEquals(entry.author, u"<unknown>")


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
            set((location_tokyo, location_man, location_zero)),
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
                    # Make sure that the incident numbers vended by data()
                    # match the next_incident_number() implementation.
                    assert incident.number == store.next_incident_number()
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
            # Make sure that the incident numbers vended by data()
            # match the next_incident_number() implementation.
            assert incident.number == store.next_incident_number()
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

    def next_number():
        number_container[0] += 1
        return number_container[0]
    number_container = [0]

    return (
        Incident(
            number=next_number(),
            rangers=(), incident_types=(), priority=5,
            created=time1,
            report_entries=(
                ReportEntry(u"Tool", u"Man overboard!", time1),
                ReportEntry(u"Splinter", u"What?", time2),
            ),
            location=location_tokyo,
        ),
        Incident(
            number=next_number(),
            rangers=(), incident_types=(), priority=5,
            created=time3,
            report_entries=(
                ReportEntry(u"El Weso", u"Does this work?", time3),
            ),
            location=location_zero,
        ),
        Incident(
            number=next_number(),
            rangers=(), incident_types=(), priority=5,
            created=time2,
            report_entries=(
                ReportEntry(u"Librarian", u"Go read something.", time2),
            ),
            location=location_man,
        ),
        Incident(
            number=next_number(),
            rangers=(), incident_types=(), priority=5,
            created=time1, state=IncidentState.closed,
            report_entries=(
                ReportEntry(u"da Mongolian", u"Fire!", time2),
            ),
        ),
    )


test_incident_etags = {
    1: u"bbf50b1c73a5462e2ec45f789b16e4c2d7cfb0ea",
    2: u"e130c7cba55c1271ba855c1273fbc8974be2b559",
    3: u"f32749ad84344959dbdf001f976881f9b336d170",
    4: u"a1bfe51a1fb342c256f710896bb160875aa73460",
}


def list_incidents(numbers=test_incident_etags):
    return ((i, test_incident_etags[i]) for i in numbers)


time1 = DateTime(2012, 9, 1, 21, 0, 0, tzinfo=utc)
time2 = DateTime(2013, 8, 31, 21, 0, 0, tzinfo=utc)
time3 = DateTime(2014, 8, 23, 21, 0, 0, tzinfo=utc)
