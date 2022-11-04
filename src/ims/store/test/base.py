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
from collections.abc import Sequence
from datetime import datetime as DateTime
from datetime import timedelta as TimeDelta
from typing import ClassVar

from attrs import mutable

from ims.ext.trial import AsynchronousTestCase
from ims.model import Event, Incident, IncidentReport, ReportEntry

from .._abc import IMSDataStore


__all__ = ()


@mutable(kw_only=True)
class TestDataStoreMixIn(ABC):
    """
    :class:`IMSDataStore` mix-in for testing.
    """

    maxIncidentNumber: ClassVar[int] = 2**63 - 1  # Default to 64-bit int
    exceptionClass: ClassVar[type] = Exception
    exceptionMessage: ClassVar[str] = "I'm broken, yo"

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
    async def storeEvent(self, event: Event) -> None:
        """
        Store the given event in the test store.
        """

    @abstractmethod
    async def storeIncident(self, incident: Incident) -> None:
        """
        Store the given incident in the test store.
        """

    @abstractmethod
    async def storeIncidentReport(self, incidentReport: IncidentReport) -> None:
        """
        Store the given incident report in the test store.
        """

    @abstractmethod
    async def storeConcentricStreet(
        self,
        eventID: str,
        streetID: str,
        streetName: str,
        ignoreDuplicates: bool = False,
    ) -> None:
        """
        Store a street in the given event with the given ID and name in the
        test store.
        """

    @abstractmethod
    async def storeIncidentType(self, name: str, hidden: bool) -> None:
        """
        Store an incident type with the given name and hidden state in the
        test store.
        """

    def dateTimesEqual(self, a: DateTime, b: DateTime) -> bool:
        """
        Compare two :class:`DateTime` objects.
        Apply some "close enough" logic to deal with the possibility that
        date-times stored in a database may be slightly off when retrieved.
        """
        # Floats stored may be slightly off when round-tripped.
        return a - b < TimeDelta(microseconds=20)

    def reportEntriesEqual(
        self,
        reportEntriesA: Sequence[ReportEntry],
        reportEntriesB: Sequence[ReportEntry],
        ignoreAutomatic: bool = False,
    ) -> bool:
        """
        Compare two sequences of :class:`ReportEntry` objects, using
        :meth:`dateTimesEqual` when comparing date-times.
        """
        if ignoreAutomatic:
            reportEntriesA = tuple(e for e in reportEntriesA if not e.automatic)

        if len(reportEntriesA) != len(reportEntriesB):
            return False

        for entryA, entryB in zip(reportEntriesA, reportEntriesB):
            if entryA != entryB:
                if entryA.author != entryB.author:
                    return False
                if entryA.automatic != entryB.automatic:
                    return False
                if entryA.text != entryB.text:
                    return False
                if not self.dateTimesEqual(entryA.created, entryB.created):
                    return False

        return True

    @staticmethod
    def normalizeIncidentAddress(incident: Incident) -> Incident:
        """
        Normalize the address in an incident to a canonical form, if necessary.
        """
        return incident


@mutable(kw_only=True)
class TestDataStoreABC(IMSDataStore, TestDataStoreMixIn):
    """
    Test Data Store ABC.
    """


class DataStoreTests(AsynchronousTestCase):
    """
    Tests for :class:`IMSDataStore` event access.
    """

    skip: ClassVar[str | None] = "Parent class of real tests"

    async def store(self) -> TestDataStoreABC:
        """
        Return a data store for use in tests.
        """
        raise NotImplementedError("Subclass should implement store()")
