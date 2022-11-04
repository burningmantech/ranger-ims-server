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
Report tests for :mod:`ranger-ims-server.store`
"""

from collections.abc import Awaitable, Callable, Iterable, Sequence
from datetime import datetime as DateTime
from datetime import timedelta as TimeDelta
from datetime import timezone as TimeZone
from typing import Any, cast

from attr import fields as attrFields

from ims.ext.trial import asyncAsDeferred
from ims.model import Event, IncidentReport, ReportEntry

from .._exceptions import NoSuchIncidentReportError, StorageError
from .base import DataStoreTests, TestDataStoreABC
from .incident import anEvent, anIncident1, aReportEntry


__all__ = ()


# Note: we add a TimeDelta to the created attribute of objects so that they
# don't have timestamps that are within the time resolution of some back-end
# data stores.

aNewIncidentReport = IncidentReport(
    eventID=anEvent.id,
    number=0,
    created=DateTime.now(TimeZone.utc) + TimeDelta(seconds=1),
    summary="A funny thing happened",
    incidentNumber=None,
    reportEntries=(),
)

anIncidentReport1 = IncidentReport(
    eventID=anEvent.id,
    number=1,
    created=DateTime.now(TimeZone.utc) + TimeDelta(seconds=2),
    summary="A scary thing happened",
    incidentNumber=None,
    reportEntries=(),
)

anIncidentReport2 = IncidentReport(
    eventID=anEvent.id,
    number=2,
    created=DateTime.now(TimeZone.utc) + TimeDelta(seconds=3),
    summary="A sad thing happened",
    incidentNumber=None,
    reportEntries=(),
)

aReportEntry1 = ReportEntry(
    created=DateTime.now(TimeZone.utc) + TimeDelta(seconds=4),
    author="Hubcap",
    automatic=False,
    text="Well there was thing thing",
)

aReportEntry2 = ReportEntry(
    created=DateTime.now(TimeZone.utc) + TimeDelta(seconds=5),
    author="Bucket",
    automatic=False,
    text="Well there was that thing",
)


class DataStoreIncidentReportTests(DataStoreTests):
    """
    Tests for :class:`DataStore` incident report access.
    """

    @asyncAsDeferred
    async def test_incidentReports(self) -> None:
        """
        :meth:`DataStore.incidentReports` returns all incident reports attached
        to an incident in an event.
        """
        for _incidentReports in (
            (),
            (anIncidentReport1,),
            (anIncidentReport1, anIncidentReport2),
        ):
            incidentReports = cast(Iterable[IncidentReport], _incidentReports)
            incidentReportsByNumber = {
                r.number: r.replace(incidentNumber=anIncident1.number)
                for r in incidentReports
            }

            store = await self.store()
            await store.storeIncident(anIncident1)

            for incidentReport in incidentReports:
                await store.storeIncidentReport(incidentReport)
                await store.attachIncidentReportToIncident(
                    incidentReport.number,
                    anIncident1.eventID,
                    anIncident1.number,
                    "HubCap",
                )

            found: set[int] = set()
            for retrieved in await store.incidentReports(anIncident1.eventID):
                self.assertIn(retrieved.number, incidentReportsByNumber)
                self.assertIncidentReportsEqual(
                    store,
                    retrieved,
                    incidentReportsByNumber[retrieved.number],
                    ignoreAutomatic=True,
                )
                found.add(retrieved.number)

            self.assertEqual(found, {r.number for r in incidentReports})

    @asyncAsDeferred
    async def test_incidentReports_error(self) -> None:
        """
        :meth:`DataStore.incidentReports` raises :exc:`StorageError` when
        the database raises an exception.
        """
        store = await self.store()
        store.bringThePain()

        try:
            await store.incidentReports(anEvent.id)
        except StorageError as e:
            self.assertEqual(str(e), store.exceptionMessage)
        else:
            self.fail("StorageError not raised")

    @asyncAsDeferred
    async def test_incidentReportWithNumber(self) -> None:
        """
        :meth:`DataStore.incidentReportWithNumber` returns the specified
        incident report.
        """
        for incidentReport in (anIncidentReport1, anIncidentReport2):
            store = await self.store()
            await store.storeIncidentReport(incidentReport)

            retrieved = await store.incidentReportWithNumber(
                anEvent.id, incidentReport.number
            )

            self.assertIncidentReportsEqual(store, retrieved, incidentReport)

    @asyncAsDeferred
    async def test_incidentReportWithNumber_notFound(self) -> None:
        """
        :meth:`DataStore.incidentReportWithNumber` raises
        :exc:`NoSuchIncidentReportError` when the given incident report number
        is not found.
        """
        store = await self.store()

        try:
            await store.incidentReportWithNumber(anEvent.id, 1)
        except NoSuchIncidentReportError:
            pass
        else:
            self.fail("NoSuchIncidentReportError not raised")

    @asyncAsDeferred
    async def test_incidentReportWithNumber_tooBig(self) -> None:
        """
        :meth:`DataStore.incidentReportWithNumber` raises
        :exc:`NoSuchIncidentReportError` when the given incident report number
        is too large for the database.
        """
        store = await self.store()

        try:
            await store.incidentReportWithNumber(
                anEvent.id, store.maxIncidentNumber + 1
            )
        except NoSuchIncidentReportError:
            pass
        else:
            self.fail("NoSuchIncidentReportError not raised")

    @asyncAsDeferred
    async def test_incidentReportWithNumber_error(self) -> None:
        """
        :meth:`DataStore.incidentReportWithNumber` raises :exc:`StorageError`
        when the given incident report number is too large for the database.
        """
        store = await self.store()
        store.bringThePain()

        try:
            await store.incidentReportWithNumber(anEvent.id, 1)
        except StorageError as e:
            self.assertEqual(str(e), store.exceptionMessage)
        else:
            self.fail("StorageError not raised")

    @asyncAsDeferred
    async def test_createIncidentReport(self) -> None:
        """
        :meth:`DataStore.createIncidentReport` creates the given incident
        report.
        """
        for _data in (
            (),
            ((anIncidentReport1.replace(number=0), "Hubcap"),),
            (
                (anIncidentReport1.replace(number=0), "Hubcap"),
                (anIncidentReport2.replace(number=0), "Bucket"),
            ),
        ):
            data = cast(Iterable[tuple[IncidentReport, str]], _data)

            store = await self.store()
            await store.createEvent(anEvent)

            expectedStoredIncidentReports: set[IncidentReport] = set()
            nextNumber = 1

            for incidentReport, author in data:
                retrieved = await store.createIncidentReport(
                    incidentReport=incidentReport, author=author
                )
                expected = incidentReport.replace(number=nextNumber)

                self.assertIncidentReportsEqual(
                    store, retrieved, expected, ignoreAutomatic=True
                )

                expectedStoredIncidentReports.add(expected)
                nextNumber += 1

            storedIncidentReports = sorted(
                await store.incidentReports(anEvent.id)
            )

            self.assertEqual(
                len(storedIncidentReports), len(expectedStoredIncidentReports)
            )

            for stored, expected in zip(
                storedIncidentReports, sorted(expectedStoredIncidentReports)
            ):
                self.assertIncidentReportsEqual(
                    store, stored, expected, ignoreAutomatic=True
                )

    @asyncAsDeferred
    async def test_createIncidentReport_error(self) -> None:
        """
        :meth:`DataStore.createIncidentReport` raises :exc:`StorageError` when
        the database raises an exception.
        """
        store = await self.store()
        await store.createEvent(Event(id=aNewIncidentReport.eventID))
        store.bringThePain()

        try:
            await store.createIncidentReport(aNewIncidentReport, "Hubcap")
        except StorageError as e:
            self.assertEqual(str(e), store.exceptionMessage)
        else:
            self.fail("StorageError not raised")

    @asyncAsDeferred
    async def test_setIncidentReport_summary_error(self) -> None:
        """
        :meth:`DataStore.setIncident_summary` raises :exc:`StorageError` when
        the database raises an exception.
        """
        store = await self.store()
        await store.storeIncidentReport(anIncidentReport1)
        store.bringThePain()

        try:
            await store.setIncidentReport_summary(
                anIncidentReport1.eventID,
                anIncidentReport1.number,
                "Never mind",
                "Bucket",
            )
        except StorageError as e:
            self.assertEqual(str(e), store.exceptionMessage)
        else:
            self.fail("StorageError not raised")

    async def _test_setIncidentReportAttribute(
        self,
        incidentReport: IncidentReport,
        methodName: str,
        attributeName: str,
        value: Any,
    ) -> None:
        store = await self.store()
        await store.storeIncidentReport(incidentReport)

        setter = cast(
            Callable[[str, int, str, str], Awaitable[None]],
            getattr(store, methodName),
        )

        await setter(
            incidentReport.eventID, incidentReport.number, value, "Hubcap"
        )

        retrieved = await store.incidentReportWithNumber(
            incidentReport.eventID, incidentReport.number
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
            store, retrieved, incidentReport, ignoreAutomatic=True
        )

    @asyncAsDeferred
    async def test_setIncidentReport_summary(self) -> None:
        """
        :meth:`DataStore.setIncidentReport_summary` updates the summary for the
        given incident report in the data store.
        """
        for incidentReport, summary in (
            (anIncidentReport1, "foo bar"),
            (anIncidentReport2, ""),
        ):
            await self._test_setIncidentReportAttribute(
                incidentReport, "setIncidentReport_summary", "summary", summary
            )

    @asyncAsDeferred
    async def test_addReportEntriesToIncidentReport(self) -> None:
        """
        :meth:`DataStore.addReportEntriesToIncidentReport` adds the given
        report entries to the given incident report in the data store.
        """
        incidentReport = anIncidentReport1
        author = "Bucket"

        for reportEntries in (
            frozenset(()),
            frozenset((aReportEntry1,)),
            frozenset((aReportEntry1, aReportEntry2)),
        ):
            # Change author in report entries to match the author so we will
            # use to add them
            reportEntries = frozenset(
                r.replace(author=author)
                for r in cast(Iterable[ReportEntry], reportEntries)
            )

            # Store test data
            store = await self.store()
            await store.storeIncidentReport(incidentReport)

            # Fetch incident report back so we have the version from the DB
            incidentReport = await store.incidentReportWithNumber(
                anEvent.id, incidentReport.number
            )
            originalEntries = frozenset(incidentReport.reportEntries)

            # Add report entries
            await store.addReportEntriesToIncidentReport(
                anEvent.id, incidentReport.number, reportEntries, author
            )

            # Get the updated incident report with the new report entries
            updated = await store.incidentReportWithNumber(
                anEvent.id, incidentReport.number
            )
            updatedEntries = frozenset(updated.reportEntries)

            # Updated entries minus the original entries == the added entries
            updatedNewEntries = updatedEntries - originalEntries
            self.assertTrue(
                store.reportEntriesEqual(
                    sorted(updatedNewEntries), sorted(reportEntries)
                )
            )

    @asyncAsDeferred
    async def test_addReportEntriesToIncidentReport_automatic(self) -> None:
        """
        :meth:`DataStore.addReportEntriesToIncidentReport` raises
        :exc:`ValueError` when given automatic report entries.
        """
        store = await self.store()
        await store.storeIncidentReport(anIncidentReport1)

        reportEntry = aReportEntry.replace(automatic=True)

        try:
            await store.addReportEntriesToIncidentReport(
                anIncidentReport1.eventID,
                anIncidentReport1.number,
                (reportEntry,),
                reportEntry.author,
            )
        except ValueError as e:
            self.assertIn(" may not be created by user ", str(e))
        else:
            self.fail("ValueError not raised")

    @asyncAsDeferred
    async def test_addReportEntriesToIncidentReport_wrongAuthor(self) -> None:
        """
        :meth:`DataStore.addReportEntriesToIncidentReport` raises
        :exc:`ValueError` when given report entries with an author that does
        not match the author that is adding the entries.
        """
        store = await self.store()
        await store.storeIncidentReport(anIncidentReport1)

        otherAuthor = f"not{aReportEntry.author}"

        try:
            await store.addReportEntriesToIncidentReport(
                anIncidentReport1.eventID,
                anIncidentReport1.number,
                (aReportEntry,),
                otherAuthor,
            )
        except ValueError as e:
            self.assertEndsWith(str(e), f" has author != {otherAuthor}")
        else:
            self.fail("ValueError not raised")

    @asyncAsDeferred
    async def test_addReportEntriesToIncidentReport_error(self) -> None:
        """
        :meth:`DataStore.addReportEntriesToIncidentReport` raises
        :exc:`StorageError` when the database raises an exception.
        """
        store = await self.store()
        await store.storeIncidentReport(anIncidentReport1)
        store.bringThePain()

        try:
            await store.addReportEntriesToIncidentReport(
                anIncidentReport1.eventID,
                anIncidentReport1.number,
                (aReportEntry,),
                aReportEntry.author,
            )
        except StorageError as e:
            self.assertEqual(str(e), store.exceptionMessage)
        else:
            self.fail("StorageError not raised")

    @asyncAsDeferred
    async def test_incidentReportsAttachedToIncident_error(self) -> None:
        """
        :meth:`DataStore.incidentReportsAttachedToIncident` raises
        :exc:`StorageError` when the database raises an exception.
        """
        store = await self.store()
        await store.storeIncidentReport(anIncidentReport1)
        store.bringThePain()

        try:
            await store.incidentReportsAttachedToIncident(
                anIncidentReport1.eventID, anIncidentReport1.number
            )
        except StorageError as e:
            self.assertEqual(str(e), store.exceptionMessage)
        else:
            self.fail("StorageError not raised")

    @asyncAsDeferred
    async def test_attachIncidentReportToIncident_error(self) -> None:
        """
        :meth:`DataStore.attachIncidentReportToIncident` raises
        :exc:`StorageError` when the database raises an exception.
        """
        store = await self.store()
        await store.storeIncident(anIncident1)
        await store.storeIncidentReport(anIncidentReport1)
        store.bringThePain()

        try:
            await store.attachIncidentReportToIncident(
                anIncidentReport1.number,
                anIncident1.eventID,
                anIncident1.number,
                "Hubcap",
            )
        except StorageError as e:
            self.assertEqual(str(e), store.exceptionMessage)
        else:
            self.fail("StorageError not raised")

    @asyncAsDeferred
    async def test_detachIncidentReportFromIncident_error(self) -> None:
        """
        :meth:`DataStore.detachIncidentReportFromIncident` raises
        :exc:`StorageError` when the database raises an exception.
        """
        store = await self.store()
        await store.storeIncident(anIncident1)
        await store.storeIncidentReport(anIncidentReport1)

        await store.attachIncidentReportToIncident(
            anIncidentReport1.number,
            anIncident1.eventID,
            anIncident1.number,
            "Hubcap",
        )
        store.bringThePain()

        try:
            await store.detachIncidentReportFromIncident(
                anIncidentReport1.number,
                anIncident1.eventID,
                anIncident1.number,
                "Hubcap",
            )
        except StorageError as e:
            self.assertEqual(str(e), store.exceptionMessage)
        else:
            self.fail("StorageError not raised")

    def assertMultipleIncidentReportsEqual(
        self,
        store: TestDataStoreABC,
        groupA: Sequence[IncidentReport],
        groupB: Sequence[IncidentReport],
        ignoreAutomatic: bool = False,
    ) -> None:
        self.assertEqual(len(groupA), len(groupB))

        bByNumber = {r.number: r for r in groupB}

        for a in groupA:
            self.assertIn(a.number, bByNumber)
            self.assertIncidentReportsEqual(store, a, bByNumber[a.number])

    def assertIncidentReportsEqual(
        self,
        store: TestDataStoreABC,
        incidentReportA: IncidentReport,
        incidentReportB: IncidentReport,
        ignoreAutomatic: bool = False,
    ) -> None:
        if incidentReportA != incidentReportB:
            messages = []

            for attribute in attrFields(IncidentReport):
                name = attribute.name
                valueA = getattr(incidentReportA, name)
                valueB = getattr(incidentReportB, name)

                if name == "created":
                    if store.dateTimesEqual(valueA, valueB):
                        continue
                    else:
                        messages.append(f"{name} delta: {valueA - valueB}")
                elif name == "reportEntries":
                    if store.reportEntriesEqual(
                        valueA, valueB, ignoreAutomatic
                    ):
                        continue

                if valueA != valueB:
                    messages.append(f"{name} {valueA!r} != {valueB!r}")

            if messages:
                self.fail(
                    "incident reports do not match:\n" + "\n".join(messages)
                )
