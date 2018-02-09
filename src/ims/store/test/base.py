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
Tests for :mod:`ranger-ims-server.store`
"""

from abc import ABC, abstractmethod
from typing import Dict, Set

from attr import attrs

from ims.model import Event, Incident, IncidentReport

from .._abc import IMSDataStore

Dict, Set  # silence linter


__all__ = ()



@attrs(frozen=True)
class TestDataStore(IMSDataStore, ABC):
    """
    :class:`IMSDataStore` subclass that raises a database exception when things
    get interesting.
    """

    exceptionClass = Exception
    exceptionMessage = "I'm broken, yo"


    @abstractmethod
    def bringThePain(self) -> None:
        """
        Raise exceptions on future DB queries.
        """


    def raiseException(self) -> None:
        """
        Raise a database exception.
        """
        raise self.exceptionClass(self.exceptionMessage)


    @abstractmethod
    def storeEvent(self, event: Event) -> None:
        """
        Store the given event in the test store.
        """


    @abstractmethod
    def storeIncident(self, incident: Incident) -> None:
        """
        Store the given incident in the test store.
        """


    @abstractmethod
    def storeIncidentReport(self, incidentReport: IncidentReport) -> None:
        """
        Store the given incident report in the test store.
        """
