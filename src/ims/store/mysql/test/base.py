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

from ims.ext.trial import TestCase
from ims.model import Event, Incident, IncidentReport

from .._store import DataStore
from ...test.base import TestDataStore as SuperTestDataStore


__all__ = ()



class TestDataStore(SuperTestDataStore, DataStore):
    """
    See :class:`SuperTestDataStore`.
    """

    maxIncidentNumber = 4294967295

    exceptionClass = RuntimeError


    def __init__(
        self, testCase: TestCase,
        hostname: str = "",
        database: str = "",
        username: str = "",
        password: str = "",
    ) -> None:
        DataStore.__init__(
            self,
            hostname=hostname, database=database,
            username=username, password=password,
        )


    def bringThePain(self) -> None:
        setattr(self._state, "broken", True)
        assert getattr(self._state, "broken")


    def storeEvent(self, event: Event) -> None:
        raise NotImplementedError()


    def storeIncident(self, incident: Incident) -> None:
        raise NotImplementedError()


    def storeIncidentReport(
        self, incidentReport: IncidentReport
    ) -> None:
        raise NotImplementedError()


    def storeConcentricStreet(
        self, event: Event, streetID: str, streetName: str,
        ignoreDuplicates: bool = False,
    ) -> None:
        raise NotImplementedError()


    def storeIncidentType(self, name: str, hidden: bool) -> None:
        raise NotImplementedError()


    @staticmethod
    def normalizeIncidentAddress(incident: Incident) -> Incident:
        raise NotImplementedError()
