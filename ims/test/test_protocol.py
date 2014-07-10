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

from twisted.python.filepath import FilePath
import twisted.trial.unittest
from twisted.internet.defer import inlineCallbacks

from ims.config import Configuration
from ims.store import Storage
from ims.json import json_from_text
from ims.protocol import IncidentManagementSystem

from ims.test.test_config import emptyConfigFile



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


    def ims(self):
        config = Configuration(emptyConfigFile)
        # config.storage = self.storage()
        ims = IncidentManagementSystem(config)
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
