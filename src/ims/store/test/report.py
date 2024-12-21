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

from attrs import fields as attrsFields

from ims.ext.trial import asyncAsDeferred
from ims.model import Event, FieldReport, ReportEntry

from .._exceptions import NoSuchFieldReportError, StorageError
from .base import DataStoreTests, TestDataStoreABC
from .incident import anEvent, anIncident1, aReportEntry


__all__ = ()


# Note: we add a TimeDelta to the created attribute of objects so that they
# don't have timestamps that are within the time resolution of some back-end
# data stores.

aNewFieldReport = FieldReport(
    eventID=anEvent.id,
    number=0,
    created=DateTime.now(TimeZone.utc) + TimeDelta(seconds=1),
    summary="A funny thing happened",
    incidentNumber=None,
    reportEntries=(),
)

aFieldReport1 = FieldReport(
    eventID=anEvent.id,
    number=1,
    created=DateTime.now(TimeZone.utc) + TimeDelta(seconds=2),
    summary="A scary thing happened",
    incidentNumber=None,
    reportEntries=(),
)

aFieldReport2 = FieldReport(
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


class DataStoreFieldReportTests(DataStoreTests):
    """
    Tests for :class:`DataStore` field report access.
    """

    @asyncAsDeferred
    async def test_fieldReports(self) -> None:
        """
        :meth:`DataStore.fieldReports` returns all field reports attached
        to an incident in an event.
        """
        for _fieldReports in (
            (),
            (aFieldReport1,),
            (aFieldReport1, aFieldReport2),
        ):
            fieldReports = cast(Iterable[FieldReport], _fieldReports)
            fieldReportsByNumber = {
                r.number: r.replace(incidentNumber=anIncident1.number)
                for r in fieldReports
            }

            store = await self.store()
            await store.storeIncident(anIncident1)

            for fieldReport in fieldReports:
                await store.storeFieldReport(fieldReport)
                await store.attachFieldReportToIncident(
                    fieldReport.number,
                    anIncident1.eventID,
                    anIncident1.number,
                    "HubCap",
                )

            found: set[int] = set()
            for retrieved in await store.fieldReports(anIncident1.eventID):
                self.assertIn(retrieved.number, fieldReportsByNumber)
                self.assertFieldReportsEqual(
                    store,
                    retrieved,
                    fieldReportsByNumber[retrieved.number],
                    ignoreAutomatic=True,
                )
                found.add(retrieved.number)

            self.assertEqual(found, {r.number for r in fieldReports})

    @asyncAsDeferred
    async def test_fieldReports_error(self) -> None:
        """
        :meth:`DataStore.fieldReports` raises :exc:`StorageError` when
        the database raises an exception.
        """
        store = await self.store()
        store.bringThePain()

        try:
            await store.fieldReports(anEvent.id)
        except StorageError as e:
            self.assertEqual(str(e), store.exceptionMessage)
        else:
            self.fail("StorageError not raised")

    @asyncAsDeferred
    async def test_fieldReportWithNumber(self) -> None:
        """
        :meth:`DataStore.fieldReportWithNumber` returns the specified
        field report.
        """
        for fieldReport in (aFieldReport1, aFieldReport2):
            store = await self.store()
            await store.storeFieldReport(fieldReport)

            retrieved = await store.fieldReportWithNumber(
                anEvent.id, fieldReport.number
            )

            self.assertFieldReportsEqual(store, retrieved, fieldReport)

    @asyncAsDeferred
    async def test_fieldReportWithNumber_notFound(self) -> None:
        """
        :meth:`DataStore.fieldReportWithNumber` raises
        :exc:`NoSuchFieldReportError` when the given field report number
        is not found.
        """
        store = await self.store()

        try:
            await store.fieldReportWithNumber(anEvent.id, 1)
        except NoSuchFieldReportError:
            pass
        else:
            self.fail("NoSuchFieldReportError not raised")

    @asyncAsDeferred
    async def test_fieldReportWithNumber_tooBig(self) -> None:
        """
        :meth:`DataStore.fieldReportWithNumber` raises
        :exc:`NoSuchFieldReportError` when the given field report number
        is too large for the database.
        """
        store = await self.store()

        try:
            await store.fieldReportWithNumber(anEvent.id, store.maxIncidentNumber + 1)
        except NoSuchFieldReportError:
            pass
        else:
            self.fail("NoSuchFieldReportError not raised")

    @asyncAsDeferred
    async def test_fieldReportWithNumber_error(self) -> None:
        """
        :meth:`DataStore.fieldReportWithNumber` raises :exc:`StorageError`
        when the given field report number is too large for the database.
        """
        store = await self.store()
        store.bringThePain()

        try:
            await store.fieldReportWithNumber(anEvent.id, 1)
        except StorageError as e:
            self.assertEqual(str(e), store.exceptionMessage)
        else:
            self.fail("StorageError not raised")

    @asyncAsDeferred
    async def test_createFieldReport(self) -> None:
        """
        :meth:`DataStore.createFieldReport` creates the given field
        report.
        """
        for _data in (
            (),
            ((aFieldReport1.replace(number=0), "Hubcap"),),
            (
                (aFieldReport1.replace(number=0), "Hubcap"),
                (aFieldReport2.replace(number=0), "Bucket"),
            ),
        ):
            data = cast(Iterable[tuple[FieldReport, str]], _data)

            store = await self.store()
            await store.createEvent(anEvent)

            expectedStoredFieldReports: set[FieldReport] = set()
            nextNumber = 1

            for fieldReport, author in data:
                retrieved = await store.createFieldReport(
                    fieldReport=fieldReport, author=author
                )
                expected = fieldReport.replace(number=nextNumber)

                self.assertFieldReportsEqual(
                    store, retrieved, expected, ignoreAutomatic=True
                )

                expectedStoredFieldReports.add(expected)
                nextNumber += 1

            storedFieldReports = sorted(await store.fieldReports(anEvent.id))

            self.assertEqual(len(storedFieldReports), len(expectedStoredFieldReports))

            for stored, expected in zip(
                storedFieldReports,
                sorted(expectedStoredFieldReports),
                strict=True,
            ):
                self.assertFieldReportsEqual(
                    store, stored, expected, ignoreAutomatic=True
                )

    @asyncAsDeferred
    async def test_createFieldReport_error(self) -> None:
        """
        :meth:`DataStore.createFieldReport` raises :exc:`StorageError` when
        the database raises an exception.
        """
        store = await self.store()
        await store.createEvent(Event(id=aNewFieldReport.eventID))
        store.bringThePain()

        try:
            await store.createFieldReport(aNewFieldReport, "Hubcap")
        except StorageError as e:
            self.assertEqual(str(e), store.exceptionMessage)
        else:
            self.fail("StorageError not raised")

    @asyncAsDeferred
    async def test_setFieldReport_summary_error(self) -> None:
        """
        :meth:`DataStore.setFieldReport_summary` raises :exc:`StorageError` when
        the database raises an exception.
        """
        store = await self.store()
        await store.storeFieldReport(aFieldReport1)
        store.bringThePain()

        try:
            await store.setFieldReport_summary(
                aFieldReport1.eventID,
                aFieldReport1.number,
                "Never mind",
                "Bucket",
            )
        except StorageError as e:
            self.assertEqual(str(e), store.exceptionMessage)
        else:
            self.fail("StorageError not raised")

    async def _test_setFieldReportAttribute(
        self,
        fieldReport: FieldReport,
        methodName: str,
        attributeName: str,
        value: Any,
    ) -> None:
        store = await self.store()
        await store.storeFieldReport(fieldReport)

        setter = cast(
            Callable[[str, int, str, str], Awaitable[None]],
            getattr(store, methodName),
        )

        await setter(fieldReport.eventID, fieldReport.number, value, "Hubcap")

        retrieved = await store.fieldReportWithNumber(
            fieldReport.eventID, fieldReport.number
        )

        # Replace the specified field report attribute with the given value.
        # This is a bit complex because we're recursing into sub-attributes.
        attrPath = attributeName.split(".")
        values = [fieldReport]
        for a in attrPath[:-1]:
            values.append(getattr(values[-1], a))
        values.append(value)
        for a in reversed(attrPath):
            v = values.pop()
            values[-1] = values[-1].replace(**{a: v})
        fieldReport = values[0]

        self.assertFieldReportsEqual(
            store, retrieved, fieldReport, ignoreAutomatic=True
        )

    @asyncAsDeferred
    async def test_setFieldReport_summary(self) -> None:
        """
        :meth:`DataStore.setFieldReport_summary` updates the summary for the
        given field report in the data store.
        """
        for fieldReport, summary in (
            (aFieldReport1, "foo bar"),
            (aFieldReport2, ""),
        ):
            await self._test_setFieldReportAttribute(
                fieldReport, "setFieldReport_summary", "summary", summary
            )

    @asyncAsDeferred
    async def test_addReportEntriesToFieldReport(self) -> None:
        """
        :meth:`DataStore.addReportEntriesToFieldReport` adds the given
        report entries to the given field report in the data store.
        """
        fieldReport = aFieldReport1
        author = "Bucket"

        for reportEntries in (
            frozenset(()),
            frozenset((aReportEntry1,)),
            frozenset((aReportEntry1, aReportEntry2)),
        ):
            # Change author in report entries to match the author we will use to
            # add them
            reportEntries = frozenset(  # noqa: PLW2901
                r.replace(author=author)
                for r in cast(Iterable[ReportEntry], reportEntries)
            )

            # Store test data
            store = await self.store()
            await store.storeFieldReport(fieldReport)

            # Fetch field report back so we have the version from the DB
            fieldReport = await store.fieldReportWithNumber(
                anEvent.id, fieldReport.number
            )
            originalEntries = frozenset(fieldReport.reportEntries)

            # Add report entries
            await store.addReportEntriesToFieldReport(
                anEvent.id, fieldReport.number, reportEntries, author
            )

            # Get the updated field report with the new report entries
            updated = await store.fieldReportWithNumber(anEvent.id, fieldReport.number)
            updatedEntries = frozenset(updated.reportEntries)

            # Updated entries minus the original entries == the added entries
            updatedNewEntries = updatedEntries - originalEntries
            self.assertTrue(
                store.reportEntriesEqual(
                    sorted(updatedNewEntries), sorted(reportEntries)
                )
            )

    @asyncAsDeferred
    async def test_addReportEntriesToFieldReport_automatic(self) -> None:
        """
        :meth:`DataStore.addReportEntriesToFieldReport` raises
        :exc:`ValueError` when given automatic report entries.
        """
        store = await self.store()
        await store.storeFieldReport(aFieldReport1)

        reportEntry = aReportEntry.replace(automatic=True)

        try:
            await store.addReportEntriesToFieldReport(
                aFieldReport1.eventID,
                aFieldReport1.number,
                (reportEntry,),
                reportEntry.author,
            )
        except ValueError as e:
            self.assertIn(" may not be created by user ", str(e))
        else:
            self.fail("ValueError not raised")

    @asyncAsDeferred
    async def test_addReportEntriesToFieldReport_wrongAuthor(self) -> None:
        """
        :meth:`DataStore.addReportEntriesToFieldReport` raises
        :exc:`ValueError` when given report entries with an author that does
        not match the author that is adding the entries.
        """
        store = await self.store()
        await store.storeFieldReport(aFieldReport1)

        otherAuthor = f"not{aReportEntry.author}"

        try:
            await store.addReportEntriesToFieldReport(
                aFieldReport1.eventID,
                aFieldReport1.number,
                (aReportEntry,),
                otherAuthor,
            )
        except ValueError as e:
            self.assertEndsWith(str(e), f" has author != {otherAuthor}")
        else:
            self.fail("ValueError not raised")

    @asyncAsDeferred
    async def test_addReportEntriesToFieldReport_error(self) -> None:
        """
        :meth:`DataStore.addReportEntriesToFieldReport` raises
        :exc:`StorageError` when the database raises an exception.
        """
        store = await self.store()
        await store.storeFieldReport(aFieldReport1)
        store.bringThePain()

        try:
            await store.addReportEntriesToFieldReport(
                aFieldReport1.eventID,
                aFieldReport1.number,
                (aReportEntry,),
                aReportEntry.author,
            )
        except StorageError as e:
            self.assertEqual(str(e), store.exceptionMessage)
        else:
            self.fail("StorageError not raised")

    @asyncAsDeferred
    async def test_fieldReportsAttachedToIncident_error(self) -> None:
        """
        :meth:`DataStore.fieldReportsAttachedToIncident` raises
        :exc:`StorageError` when the database raises an exception.
        """
        store = await self.store()
        await store.storeFieldReport(aFieldReport1)
        store.bringThePain()

        try:
            await store.fieldReportsAttachedToIncident(
                aFieldReport1.eventID, aFieldReport1.number
            )
        except StorageError as e:
            self.assertEqual(str(e), store.exceptionMessage)
        else:
            self.fail("StorageError not raised")

    @asyncAsDeferred
    async def test_attachFieldReportToIncident_error(self) -> None:
        """
        :meth:`DataStore.attachFieldReportToIncident` raises
        :exc:`StorageError` when the database raises an exception.
        """
        store = await self.store()
        await store.storeIncident(anIncident1)
        await store.storeFieldReport(aFieldReport1)
        store.bringThePain()

        try:
            await store.attachFieldReportToIncident(
                aFieldReport1.number,
                anIncident1.eventID,
                anIncident1.number,
                "Hubcap",
            )
        except StorageError as e:
            self.assertEqual(str(e), store.exceptionMessage)
        else:
            self.fail("StorageError not raised")

    @asyncAsDeferred
    async def test_detachFieldReportFromIncident_error(self) -> None:
        """
        :meth:`DataStore.detachFieldReportFromIncident` raises
        :exc:`StorageError` when the database raises an exception.
        """
        store = await self.store()
        await store.storeIncident(anIncident1)
        await store.storeFieldReport(aFieldReport1)

        await store.attachFieldReportToIncident(
            aFieldReport1.number,
            anIncident1.eventID,
            anIncident1.number,
            "Hubcap",
        )
        store.bringThePain()

        try:
            await store.detachFieldReportFromIncident(
                aFieldReport1.number,
                anIncident1.eventID,
                anIncident1.number,
                "Hubcap",
            )
        except StorageError as e:
            self.assertEqual(str(e), store.exceptionMessage)
        else:
            self.fail("StorageError not raised")

    def assertMultipleFieldReportsEqual(
        self,
        store: TestDataStoreABC,
        groupA: Sequence[FieldReport],
        groupB: Sequence[FieldReport],
        ignoreAutomatic: bool = False,
    ) -> None:
        self.assertEqual(len(groupA), len(groupB))

        bByNumber = {r.number: r for r in groupB}

        for a in groupA:
            self.assertIn(a.number, bByNumber)
            self.assertFieldReportsEqual(store, a, bByNumber[a.number])

    def assertFieldReportsEqual(
        self,
        store: TestDataStoreABC,
        fieldReportA: FieldReport,
        fieldReportB: FieldReport,
        ignoreAutomatic: bool = False,
    ) -> None:
        if fieldReportA != fieldReportB:
            messages = []

            for attribute in attrsFields(FieldReport):
                name = attribute.name
                valueA = getattr(fieldReportA, name)
                valueB = getattr(fieldReportB, name)

                if name == "created":
                    if store.dateTimesEqual(valueA, valueB):
                        continue
                    messages.append(f"{name} delta: {valueA - valueB}")
                elif name == "reportEntries":
                    if store.reportEntriesEqual(valueA, valueB, ignoreAutomatic):
                        continue

                if valueA != valueB:
                    messages.append(f"{name} {valueA!r} != {valueB!r}")

            if messages:
                self.fail("field reports do not match:\n" + "\n".join(messages))
