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
from datetime import datetime as DateTime
from typing import Sequence

from ims.model import Event, Incident, IncidentReport, ReportEntry

from .._abc import IMSDataStore


__all__ = ()



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


    @abstractmethod
    def storeConcentricStreet(
        self, event: Event, streetID: str, streetName: str,
        ignoreDuplicates: bool = False,
    ) -> None:
        """
        Store the a street in the given event with the given ID and name in the
        test store.
        """


    def dateTimesEqual(self, a: DateTime, b: DateTime) -> bool:
        """
        Compare two :class:`DateTime` objects.
        Apply some "close enough" logic to deal with the possibility that
        date-times stored in a database may be slightly off when retrieved.
        """
        return a == b


    def reportEntriesEqual(
        self,
        reportEntriesA: Sequence[ReportEntry],
        reportEntriesB: Sequence[ReportEntry],
        ignoreAutomatic: bool = False,
    ) -> bool:
        """
        Compare two :class:`ReportEntry` objects, using :meth:`dateTimesEqual`
        when comparing date-times.
        """


    def normalizeIncidentAddress(self, incident: Incident) -> Incident:
        """
        Normalize the address in an incident to canonical form, if necessary.
        """
        return incident
