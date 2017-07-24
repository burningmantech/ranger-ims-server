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

from typing import Iterable, Set

from attr import fields as attrFields

from hypothesis import given

from ims.ext.sqlite import SQLITE_MAX_INT
from ims.model import IncidentReport
from ims.model.strategies import incidentReportLists, incidentReports

from .base import DataStoreTests, dateTimesEqualish, reportEntriesEqualish
from ..._exceptions import NoSuchIncidentReportError, StorageError

Set  # silence linter


__all__ = ()



class DataStoreIncidentReportTests(DataStoreTests):
    """
    Tests for :class:`DataStore` incident report access.
    """
    @given(incidentReportLists(maxNumber=SQLITE_MAX_INT, averageSize=3))
    def test_incidentReports(
        self, incidentReports: Iterable[IncidentReport]
    ) -> None:
        """
        :meth:`DataStore.incidentReports` returns all incidents.
        """
        incidentReports = tuple(incidentReports)
        incidentReportsByNumber = {r.number: r for r in incidentReports}

        store = self.store()

        for incidentReport in incidentReports:
            self.storeIncidentReport(store, incidentReport)

        found: Set[int] = set()
        for retrieved in self.successResultOf(store.incidentReports()):
            self.assertIn(retrieved.number, incidentReportsByNumber)
            self.assertIncidentReportsEqual(
                retrieved, incidentReportsByNumber[retrieved.number]
            )
            found.add(retrieved.number)

        self.assertEqual(found, set(r.number for r in incidentReports))


    def test_incidentReports_error(self) -> None:
        """
        :meth:`DataStore.incidentReports` raises :exc:`StorageError` when
        SQLite raises an exception.
        """
        store = self.store()
        store.bringThePain()

        f = self.failureResultOf(store.incidentReports())
        self.assertEqual(f.type, StorageError)


    @given(incidentReports(maxNumber=SQLITE_MAX_INT))
    def test_incidentReportWithNumber(
        self, incidentReport: IncidentReport
    ) -> None:
        """
        :meth:`DataStore.incidentReportWithNumber` returns the specified
        incident report.
        """
        store = self.store()

        self.storeIncidentReport(store, incidentReport)

        retrieved = self.successResultOf(
            store.incidentReportWithNumber(incidentReport.number)
        )

        self.assertIncidentReportsEqual(retrieved, incidentReport)


    def test_incidentReportWithNumber_notFound(self) -> None:
        """
        :meth:`DataStore.incidentReportWithNumber` raises
        :exc:`NoSuchIncidentReportError` when the given incident report number
        is not found.
        """
        store = self.store()

        f = self.failureResultOf(
            store.incidentReportWithNumber(1)
        )
        f.printTraceback()
        self.assertEqual(f.type, NoSuchIncidentReportError)


    def assertIncidentReportsEqual(
        self, incidentReportA: IncidentReport, incidentReportB: IncidentReport,
        ignoreAutomatic: bool = False,
    ) -> None:
        if incidentReportA != incidentReportB:
            messages = []

            for attribute in attrFields(IncidentReport):
                name = attribute.name
                valueA = getattr(incidentReportA, name)
                valueB = getattr(incidentReportB, name)

                if name == "created":
                    if dateTimesEqualish(valueA, valueB):
                        continue
                    else:
                        messages.append(
                            "{name} delta: {delta}"
                            .format(name=name, delta=valueA - valueB)
                        )
                elif name == "reportEntries":
                    if reportEntriesEqualish(valueA, valueB, ignoreAutomatic):
                        continue

                if valueA != valueB:
                    messages.append(
                        "{name} {valueA!r} != {valueB!r}"
                        .format(name=name, valueA=valueA, valueB=valueB)
                    )

            if messages:
                self.fail(
                    "incident reports do not match:\n" + "\n".join(messages)
                )
