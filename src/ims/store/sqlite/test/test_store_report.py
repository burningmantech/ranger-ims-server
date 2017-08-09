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

from datetime import datetime as DateTime, timezone as TimeZone
from typing import Any, FrozenSet, Iterable, List, Sequence, Set, Tuple

from attr import fields as attrFields

from hypothesis import assume, given, settings
from hypothesis.strategies import frozensets, lists, tuples

from ims.ext.sqlite import SQLITE_MAX_INT
from ims.model import Incident, IncidentReport, ReportEntry
from ims.model.strategies import (
    incidentReportLists, incidentReportSummaries, incidentReports,
    incidents, rangerHandles, reportEntries,
)

from .base import DataStoreTests, dateTimesEqualish, reportEntriesEqualish
from .test_store_incident import aReportEntry, anIncident
from ..._exceptions import NoSuchIncidentReportError, StorageError

Set  # silence linter


__all__ = ()


anIncidentReport = IncidentReport(
    number=0,
    created=DateTime.now(TimeZone.utc),
    summary="A thing happened",
    reportEntries=(),
)



class DataStoreIncidentReportTests(DataStoreTests):
    """
    Tests for :class:`DataStore` incident report access.
    """
    @given(incidentReportLists(maxNumber=SQLITE_MAX_INT, averageSize=3))
    @settings(max_examples=100)
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


    def test_incidentReportWithNumber_tooBig(self) -> None:
        """
        :meth:`DataStore.incidentReportWithNumber` raises
        :exc:`NoSuchIncidentReportError` when the given incident report number
        is too large for SQLite.
        """
        store = self.store()

        f = self.failureResultOf(
            store.incidentReportWithNumber(SQLITE_MAX_INT + 1)
        )
        self.assertEqual(f.type, NoSuchIncidentReportError)


    def test_incidentReportWithNumber_error(self) -> None:
        """
        :meth:`DataStore.incidentReportWithNumber` raises
        :exc:`NoSuchIncidentReportError` when the given incident report number
        is too large for SQLite.
        """
        store = self.store()
        store.bringThePain()

        f = self.failureResultOf(store.incidentReportWithNumber(1))
        self.assertEqual(f.type, StorageError)


    @given(
        lists(
            tuples(incidentReports(new=True), rangerHandles()),
            average_size=2
        ),
    )
    def test_createIncidentReport(
        self, data: Iterable[Tuple[IncidentReport, str]]
    ) -> None:
        """
        :meth:`DataStore.createIncidentReport` creates the given incident
        report.
        """
        store = self.store()

        expectedStoredIncidentReports: Set[IncidentReport] = set()
        nextNumber = 1

        for incidentReport, author in data:
            retrieved = self.successResultOf(
                store.createIncidentReport(
                    incidentReport=incidentReport, author=author
                )
            )
            expected = incidentReport.replace(number=nextNumber)

            self.assertIncidentReportsEqual(
                retrieved, expected, ignoreAutomatic=True
            )

            expectedStoredIncidentReports.add(expected)
            nextNumber += 1

        storedIncidentReports = sorted(
            self.successResultOf(store.incidentReports())
        )

        self.assertEqual(
            len(storedIncidentReports), len(expectedStoredIncidentReports)
        )

        for stored, expected in zip(
            storedIncidentReports, sorted(expectedStoredIncidentReports)
        ):
            self.assertIncidentReportsEqual(
                stored, expected, ignoreAutomatic=True
            )


    def test_createIncidentReport_error(self) -> None:
        """
        :meth:`DataStore.createIncidentReport` raises :exc:`StorageError` when
        SQLite raises an exception.
        """
        store = self.store()
        store.bringThePain()

        f = self.failureResultOf(
            store.createIncidentReport(anIncidentReport, "Hubcap")
        )
        self.assertEqual(f.type, StorageError)


    def test_setIncidentReport_summary_error(self) -> None:
        """
        :meth:`DataStore.setIncident_summary` raises :exc:`StorageError` when
        SQLite raises an exception.
        """
        store = self.store()
        incidentReport = self.successResultOf(
            store.createIncidentReport(anIncidentReport, "Hubcap")
        )
        store.bringThePain()

        f = self.failureResultOf(
            store.setIncidentReport_summary(
                incidentReport.number, "Never mind", "Bucket"
            )
        )
        self.assertEqual(f.type, StorageError)


    def _test_setIncidentReportAttribute(
        self, incidentReport: IncidentReport,
        methodName: str, attributeName: str, value: Any
    ) -> None:
        store = self.store()

        self.storeIncidentReport(store, incidentReport)

        setter = getattr(store, methodName)

        self.successResultOf(
            setter(incidentReport.number, value, "Hubcap")
        )

        retrieved = self.successResultOf(
            store.incidentReportWithNumber(incidentReport.number)
        )

        # Replace the specified incident attribute with the given value.
        # This is a bit complex because we're recursing into sub-attributes.
        attrPath = attributeName.split(".")
        values = [incidentReport]
        for a in attrPath[:-1]:
            values.append(getattr(values[-1], a))
        values.append(value)
        for a in reversed(attrPath):
            v = values.pop()
            values[-1] = values[-1].replace(**{a: v})
        incidentReport = values[0]

        self.assertIncidentReportsEqual(
            retrieved, incidentReport, ignoreAutomatic=True
        )


    @given(incidentReports(new=True), incidentReportSummaries())
    def test_setIncidentReport_summary(
        self, incidentReport: IncidentReport, summary: str
    ) -> None:
        """
        :meth:`DataStore.setIncidentReport_summary` updates the summary for the
        given incident report in the data store.
        """
        self._test_setIncidentReportAttribute(
            incidentReport, "setIncidentReport_summary", "summary", summary
        )


    @given(
        incidentReports(new=True),
        frozensets(reportEntries(automatic=False), average_size=2),
        rangerHandles(),
    )
    def test_addReportEntriesToIncidentReport(
        self, incidentReport: IncidentReport,
        reportEntries: FrozenSet[ReportEntry], author: str
    ) -> None:
        """
        :meth:`DataStore.addReportEntriesToIncidentReport` adds the given
        report entries to the given incident report in the data store.
        """
        # Change author in report entries to match the author so we will use to
        # add them
        reportEntries = frozenset(
            r.replace(author=author) for r in reportEntries
        )

        # Store test data
        store = self.store()
        self.storeIncidentReport(store, incidentReport)

        # Fetch incident report back so we have the version from the DB
        incidentReport = self.successResultOf(
            store.incidentReportWithNumber(incidentReport.number)
        )
        originalEntries = frozenset(incidentReport.reportEntries)

        # Add report entries
        self.successResultOf(
            store.addReportEntriesToIncidentReport(
                incidentReport.number, reportEntries, author
            )
        )

        # Get the updated incident report with the new report entries
        updated = self.successResultOf(
            store.incidentReportWithNumber(incidentReport.number)
        )
        updatedEntries = frozenset(updated.reportEntries)

        # Updated entries minus the original entries == the added entries
        updatedNewEntries = updatedEntries - originalEntries
        self.assertTrue(
            reportEntriesEqualish(
                sorted(updatedNewEntries), sorted(reportEntries)
            )
        )


    def test_addReportEntriesToIncidentReport_automatic(self) -> None:
        """
        :meth:`DataStore.addReportEntriesToIncidentReport` raises
        :exc:`ValueError` when given automatic report entries.
        """
        store = self.store()
        incidentReport = self.successResultOf(
            store.createIncidentReport(anIncidentReport, "Hubcap")
        )

        reportEntry = aReportEntry.replace(automatic=True)

        f = self.failureResultOf(
            store.addReportEntriesToIncidentReport(
                incidentReport.number, (reportEntry,), reportEntry.author
            )
        )
        self.assertEqual(f.type, ValueError)
        self.assertIn(" may not be created by user ", f.getErrorMessage())


    def test_addReportEntriesToIncidentReport_wrongAuthor(self) -> None:
        """
        :meth:`DataStore.addReportEntriesToIncidentReport` raises
        :exc:`ValueError` when given report entries with an author that does
        not match the author that is adding the entries.
        """
        store = self.store()
        incidentReport = self.successResultOf(
            store.createIncidentReport(anIncidentReport, "Hubcap")
        )

        otherAuthor = f"not{aReportEntry.author}"

        f = self.failureResultOf(
            store.addReportEntriesToIncidentReport(
                incidentReport.number, (aReportEntry,), otherAuthor
            )
        )
        self.assertEqual(f.type, ValueError)
        self.assertEndsWith(
            f.getErrorMessage(), f" has author != {otherAuthor}"
        )


    def test_addReportEntriesToIncidentReport_error(self) -> None:
        """
        :meth:`DataStore.addReportEntriesToIncidentReport` raises
        :exc:`StorageError` when SQLite raises an exception.
        """
        store = self.store()
        incidentReport = self.successResultOf(
            store.createIncidentReport(anIncidentReport, "Hubcap")
        )
        store.bringThePain()

        aReportEntry

        f = self.failureResultOf(
            store.addReportEntriesToIncidentReport(
                incidentReport.number, (aReportEntry,), aReportEntry.author
            )
        )
        self.assertEqual(f.type, StorageError)


    @given(
        incidentReportLists(averageSize=2),
        lists(
            tuples(
                incidents(new=True),
                incidentReportLists(minSize=1, averageSize=2),
            ),
            average_size=2,
        ),
    )
    @settings(max_examples=100)
    def test_detachedAndAttachedIncidentReports(
        self,
        detached: List[IncidentReport],
        attached: Sequence[Tuple[Incident, List[IncidentReport]]],
    ) -> None:
        """
        :meth:`DataStore.attachIncidentReportToIncident` attaches the given
        incident report to the given incident,
        :meth:`DataStore.incidentReportsAttachedToIncident` retrieves the
        attached incident reports, and
        :meth:`DataStore.detachedIncidentReports` retrieves unattached incident
        reports.
        """
        store = self.store()

        foundIncidentNumbers: Set[int] = set()
        foundIncidentReportNumbers: Set[int] = set()
        attachedReports: Set[IncidentReport] = set()

        # Create some detached incident reports
        for incidentReport in detached:
            self.storeIncidentReport(store, incidentReport)
            foundIncidentReportNumbers.add(incidentReport.number)

        # Create some incidents and, for each, create some incident reports
        # and attached them to the incident.
        for incident, reports in attached:
            assume(incident.number not in foundIncidentNumbers)

            self.storeIncident(store, incident)
            for incidentReport in reports:
                assume(incidentReport.number not in foundIncidentReportNumbers)

                self.storeIncidentReport(store, incidentReport)
                self.successResultOf(
                    store.attachIncidentReportToIncident(
                        incidentReport.number, incident.event, incident.number
                    )
                )
                attachedReports.add(incidentReport)

                foundIncidentReportNumbers.add(incidentReport.number)

                # Verify that the same attached incident comes back from the
                # store.
                storedAttachedIncidents = tuple(self.successResultOf(
                    store.incidentsAttachedToIncidentReport(
                        incidentReport.number
                    )
                ))
                self.assertEqual(len(storedAttachedIncidents), 1)
                self.assertEqual(
                    storedAttachedIncidents[0],
                    (incident.event, incident.number),
                )

            storedAttached = tuple(self.successResultOf(
                store.incidentReportsAttachedToIncident(
                    incident.event, incident.number
                )
            ))

            # Verify that the same attached reports come back from the store.
            self.assertMultipleIncidentReportsEqual(storedAttached, reports)

            foundIncidentNumbers.add(incident.number)

        # Verify that the same detached reports come back from the store.
        storedDetached = tuple(
            self.successResultOf(store.detachedIncidentReports())
        )
        self.assertMultipleIncidentReportsEqual(storedDetached, detached)

        # Detach everything
        for incident, reports in attached:
            for incidentReport in reports:
                self.successResultOf(
                    store.detachIncidentReportFromIncident(
                        incidentReport.number, incident.event, incident.number
                    )
                )

                # Verify report is detached
                storedAttachedIncidents = tuple(self.successResultOf(
                    store.incidentsAttachedToIncidentReport(
                        incidentReport.number
                    )
                ))
                self.assertEqual(len(storedAttachedIncidents), 0)

            # Verify no attached reports
            storedAttached = tuple(self.successResultOf(
                store.incidentReportsAttachedToIncident(
                    incident.event, incident.number
                )
            ))
            self.assertEqual(len(storedAttached), 0)


    def test_detachedIncidentReports_error(self) -> None:
        """
        :meth:`DataStore.detachedIncidentReports` raises :exc:`StorageError`
        when SQLite raises an exception.
        """
        store = self.store()
        store.bringThePain()

        f = self.failureResultOf(store.detachedIncidentReports())
        self.assertEqual(f.type, StorageError)


    def test_incidentReportsAttachedToIncident_error(self) -> None:
        """
        :meth:`DataStore.incidentReportsAttachedToIncident` raises
        :exc:`StorageError` when SQLite raises an exception.
        """
        store = self.store()
        self.successResultOf(store.createEvent(anIncident.event))
        incident = self.successResultOf(
            store.createIncident(anIncident, "Hubcap")
        )
        store.bringThePain()

        f = self.failureResultOf(
            store.incidentReportsAttachedToIncident(
                incident.event, incident.number
            )
        )
        self.assertEqual(f.type, StorageError)


    def test_incidentsAttachedToIncidentReport_error(self) -> None:
        """
        :meth:`DataStore.incidentsAttachedToIncidentReport` raises
        :exc:`StorageError` when SQLite raises an exception.
        """
        store = self.store()
        incidentReport = self.successResultOf(
            store.createIncidentReport(anIncidentReport, "Hubcap")
        )
        store.bringThePain()

        f = self.failureResultOf(
            store.incidentsAttachedToIncidentReport(incidentReport.number)
        )
        self.assertEqual(f.type, StorageError)


    def test_attachIncidentReportToIncident_error(self) -> None:
        """
        :meth:`DataStore.attachIncidentReportToIncident` raises
        :exc:`StorageError` when SQLite raises an exception.
        """
        store = self.store()
        self.successResultOf(store.createEvent(anIncident.event))
        incident = self.successResultOf(
            store.createIncident(anIncident, "Hubcap")
        )
        incidentReport = self.successResultOf(
            store.createIncidentReport(anIncidentReport, "Hubcap")
        )
        store.bringThePain()

        f = self.failureResultOf(
            store.attachIncidentReportToIncident(
                incidentReport.number, incident.event, incident.number
            )
        )
        self.assertEqual(f.type, StorageError)


    def test_detachIncidentReportFromIncident_error(self) -> None:
        """
        :meth:`DataStore.detachIncidentReportFromIncident` raises
        :exc:`StorageError` when SQLite raises an exception.
        """
        store = self.store()
        self.successResultOf(store.createEvent(anIncident.event))
        incident = self.successResultOf(
            store.createIncident(anIncident, "Hubcap")
        )
        incidentReport = self.successResultOf(
            store.createIncidentReport(anIncidentReport, "Hubcap")
        )
        self.successResultOf(
            store.attachIncidentReportToIncident(
                incidentReport.number, incident.event, incident.number
            )
        )
        store.bringThePain()

        f = self.failureResultOf(
            store.detachIncidentReportFromIncident(
                incidentReport.number, incident.event, incident.number
            )
        )
        self.assertEqual(f.type, StorageError)


    def assertMultipleIncidentReportsEqual(
        self, groupA: Sequence[IncidentReport],
        groupB: Sequence[IncidentReport], ignoreAutomatic: bool = False,
    ) -> None:
        self.assertEqual(len(groupA), len(groupB))

        bByNumber = {r.number: r for r in groupB}

        for a in groupA:
            self.assertIn(a.number, bByNumber)
            self.assertIncidentReportsEqual(a, bByNumber[a.number])


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
                        messages.append(f"{name} delta: {valueA - valueB}")
                elif name == "reportEntries":
                    if reportEntriesEqualish(valueA, valueB, ignoreAutomatic):
                        continue

                if valueA != valueB:
                    messages.append(f"{name} {valueA!r} != {valueB!r}")

            if messages:
                self.fail(
                    "incident reports do not match:\n" + "\n".join(messages)
                )
