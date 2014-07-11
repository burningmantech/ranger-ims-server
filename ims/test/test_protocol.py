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
Tests for L{ims.protocol}.
"""

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from twisted.python.filepath import FilePath
import twisted.trial.unittest
from twisted.internet.defer import inlineCallbacks

from ims.config import Configuration
from ims.store import Storage
from ims.json import json_from_text, incident_from_json
from ims.protocol import IncidentManagementSystem

from ims.test.test_config import emptyConfigFile
from ims.test.test_store import test_incidents, test_incident_etags



class IncidentManagementSystemHTTPTests(twisted.trial.unittest.TestCase):
    """
    Tests for L{IncidentManagementSystem} HTTP front-end.
    """

    def test_http(self):
        raise NotImplementedError()

    test_http.todo = "unimplemented"



class IncidentManagementSystemJSONTests(twisted.trial.unittest.TestCase):
    """
    Tests for L{IncidentManagementSystem} JSON back-end.
    """

    def storage(self, data=None):
        store = Storage(FilePath(self.mktemp()))

        store.provision()

        if data is not None:
            for incident in data(store):
                store.write_incident(incident)

        return store


    def ims(self, data=None):
        config = Configuration(emptyConfigFile)
        if data is not None:
            config.storage = self.storage(data=data)
        ims = IncidentManagementSystem(config)
        ims.avatarId = u"Tool"
        return ims


    @inlineCallbacks
    def test_data_ping(self):
        ims = self.ims()

        (entity, etag) = yield ims.data_ping()
        self.assertEquals(entity, u'"ack"')
        self.assertEquals(etag, hash(u"ack"))


    @inlineCallbacks
    def test_data_personnel(self):
        ims = self.ims()

        (entity, etag) = yield ims.data_personnel()
        json = json_from_text(entity)

        self.assertEquals(
            json,
            [
                {
                    "handle": "Easy E",
                    "name": "Eric P. Grant",
                    "status": "active",
                },
                {
                    "handle": "El Weso",
                    "name": "Wes Johnson",
                    "status": "active",
                },
                {
                    "handle": "SciFi",
                    "name": "Fred McCord",
                    "status": "active",
                },
                {
                    "handle": "Slumber",
                    "name": "Sleepy T. Drarf",
                    "status": "inactive",
                },
                {
                    "handle": "Tool",
                    "name": "Wilfredo Sanchez",
                    "status": "vintage",
                },
                {
                    "handle": "Tulsa",
                    "name": "Curtis Kline",
                    "status": "vintage",
                },
            ]
        )

        # Don't have access to the data needed to compute the same etag, so
        # just assert that there is one.
        self.assertTrue(etag)


    @inlineCallbacks
    def test_data_incident_types(self):
        ims = self.ims()

        (entity, etag) = yield ims.data_incident_types()
        self.assertEquals(entity, ims.config.IncidentTypesJSON)
        self.assertEquals(etag, hash(ims.config.IncidentTypesJSON))


    @inlineCallbacks
    def test_data_incidents_none(self):
        ims = self.ims()

        (entity, etag) = yield ims.data_incidents(ims.storage.list_incidents())

        self.assertEquals(entity, u"[]")
        self.assertIdentical(etag, None)


    @inlineCallbacks
    def test_data_incidents_some(self):
        ims = self.ims(data=test_incidents)

        (entity, etag) = yield ims.data_incidents(ims.storage.list_incidents())
        json = json_from_text(entity)

        self.assertEquals(
            json,
            list(reversed(
                [[n, e] for n, e in test_incident_etags.iteritems()]
            ))
        )
        self.assertIdentical(etag, None)


    @inlineCallbacks
    def test_data_incident(self):
        ims = self.ims(data=test_incidents)

        for number in test_incident_etags.iterkeys():
            (entity, etag) = yield ims.data_incident(number)
            incident = incident_from_json(json_from_text(entity), number)

            self.assertEquals(
                incident, ims.storage.read_incident_with_number(number)
            )
            self.assertEquals(
                etag, ims.storage.etag_for_incident_with_number(number)
            )


    @inlineCallbacks
    def test_data_incident_edit(self):
        ims = self.ims(data=test_incidents)

        number = 1

        # Unedited incident has priority = 5
        assert ims.storage.read_incident_with_number(number).priority == 5

        edits_file = StringIO(u'{"priority":2}')

        (entity, etag) = yield ims.data_incident_edit(number, edits_file)

        # Response is empty
        self.assertEquals(entity, u"")
        self.assertIdentical(etag, None)

        # Verify that the edit happened; edited incident has priority = 2
        self.assertEquals(
            ims.storage.read_incident_with_number(number).priority, 2
        )
