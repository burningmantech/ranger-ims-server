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
Tests for :mod:`ranger-ims-server.store.export._json`
"""

from io import BytesIO
from pathlib import Path
from typing import Iterable

from hypothesis import given

from ims.ext.json import jsonTextFromObject, objectFromJSONText
from ims.ext.trial import TestCase
from ims.model import (
    EventAccess, EventData, IMSData, IncidentType, KnownIncidentType
)
from ims.model._type import admin, junk
from ims.model.json import jsonObjectFromModelObject, modelObjectFromJSONObject
from ims.model.strategies import imsDatas
from ims.store import IMSDataStore
from ims.store.sqlite import DataStore as SQLiteDataStore

from .._json import JSONExporter, JSONImporter


__all__ = ()


knownIncidentTypes = frozenset((admin, junk))
knownIncidentTypesNot = frozenset(
    IncidentType(name=t.name, hidden=True) for t in knownIncidentTypes
)

# Make sure this is in sync with KnownIncidentType
assert (
    sorted(t.name for t in knownIncidentTypes) ==
    sorted(k.value for k in KnownIncidentType)
)


def addKnownIncidentTypes(imsData: IMSData) -> IMSData:
    """
    Add known incident types to imsDataIn, because that's going to be
    expected in the end result, since creating the schema will add them.
    """
    incidentTypesIn = frozenset(imsData.incidentTypes)
    incidentTypesIn |= knownIncidentTypes
    incidentTypesIn -= knownIncidentTypesNot
    return imsData.replace(incidentTypes=incidentTypesIn)



class JSONExporterTests(TestCase):
    """
    Tests for :class:`JSONExporter`
    """

    def stores(self, imsData: IMSData) -> Iterable[IMSDataStore]:
        for store in (
            SQLiteDataStore(dbPath=Path(self.mktemp())),
        ):
            self.successResultOf(store.upgradeSchema())

            importer = JSONImporter(store=store, imsData=imsData)
            self.successResultOf(importer.storeData())

            yield store


    @given(imsDatas())
    def test_asBytes(self, imsDataIn: IMSData) -> None:
        imsDataIn = addKnownIncidentTypes(imsDataIn)

        for store in self.stores(imsData=imsDataIn):
            # Export the data from that store
            exporter = JSONExporter(store=store)
            data = self.successResultOf(exporter.asBytes())
            text = data.decode("utf-8")
            json = objectFromJSONText(text)
            imsDataOut = modelObjectFromJSONObject(json, IMSData)

            # Compare result to input data
            self.assertIMSDataEqual(imsDataOut, imsDataIn)


    @given(imsDatas())
    def test_asText(self, imsDataIn: IMSData) -> None:
        imsDataIn = addKnownIncidentTypes(imsDataIn)

        for store in self.stores(imsData=imsDataIn):
            # Export the data from that store
            exporter = JSONExporter(store=store)
            text = self.successResultOf(exporter.asText())
            json = objectFromJSONText(text)
            imsDataOut = modelObjectFromJSONObject(json, IMSData)

            # Compare result to input data
            self.assertIMSDataEqual(imsDataOut, imsDataIn)


    @given(imsDatas())
    def test_asJSON(self, imsDataIn: IMSData) -> None:
        imsDataIn = addKnownIncidentTypes(imsDataIn)

        for store in self.stores(imsData=imsDataIn):
            # Export the data from that store
            exporter = JSONExporter(store=store)
            json = self.successResultOf(exporter.asJSON())
            imsDataOut = modelObjectFromJSONObject(json, IMSData)

            # Compare result to input data
            self.assertIMSDataEqual(imsDataOut, imsDataIn)


    @given(imsDatas())
    def test_imsData(self, imsDataIn: IMSData) -> None:
        imsDataIn = addKnownIncidentTypes(imsDataIn)

        for store in self.stores(imsData=imsDataIn):
            # Export the data from that store
            exporter = JSONExporter(store=store)
            imsDataOut = self.successResultOf(exporter.imsData())

            # Compare exported result to input data
            self.assertIMSDataEqual(imsDataOut, imsDataIn)



class JSONImporterTests(TestCase):
    """
    Tests for :class:`JSONImporter`
    """

    def stores(self) -> Iterable[IMSDataStore]:
        for store in (
            SQLiteDataStore(dbPath=Path(self.mktemp())),
        ):
            self.successResultOf(store.upgradeSchema())
            yield store


    @given(imsDatas())
    def test_fromIO(self, imsDataIn: IMSData) -> None:
        json = jsonObjectFromModelObject(imsDataIn)
        jsonText = jsonTextFromObject(json)
        jsonBytes = jsonText.encode("utf-8")
        jsonIO = BytesIO(jsonBytes)

        for store in self.stores():
            importer = JSONImporter.fromIO(store=store, io=jsonIO)
            self.assertIMSDataEqual(importer.imsData, imsDataIn)


    @given(imsDatas())
    def test_fromBytes(self, imsDataIn: IMSData) -> None:
        json = jsonObjectFromModelObject(imsDataIn)
        jsonText = jsonTextFromObject(json)
        jsonBytes = jsonText.encode("utf-8")

        for store in self.stores():
            importer = JSONImporter.fromBytes(store=store, jsonBytes=jsonBytes)
            self.assertIMSDataEqual(importer.imsData, imsDataIn)


    @given(imsDatas())
    def test_fromText(self, imsDataIn: IMSData) -> None:
        json = jsonObjectFromModelObject(imsDataIn)
        jsonText = jsonTextFromObject(json)

        for store in self.stores():
            importer = JSONImporter.fromText(store=store, jsonText=jsonText)
            self.assertIMSDataEqual(importer.imsData, imsDataIn)


    @given(imsDatas())
    def test_fromJSON(self, imsDataIn: IMSData) -> None:
        json = jsonObjectFromModelObject(imsDataIn)

        for store in self.stores():
            importer = JSONImporter.fromJSON(store=store, json=json)
            self.assertIMSDataEqual(importer.imsData, imsDataIn)


    @given(imsDatas())
    def test_storeData(self, imsDataIn: IMSData) -> None:
        imsDataIn = addKnownIncidentTypes(imsDataIn)

        resultOf = self.successResultOf

        for store in self.stores():
            importer = JSONImporter(store=store, imsData=imsDataIn)
            resultOf(importer.storeData())

            # Create a new IMSData with the imported data in it
            allTypesOut = frozenset(
                resultOf(store.incidentTypes(includeHidden=True))
            )
            visibleTypesOut = frozenset(
                resultOf(store.incidentTypes(includeHidden=False))
            )
            imsDataOut = IMSData(
                events=(
                    EventData(
                        event=event,
                        access=EventAccess(
                            readers=resultOf(store.readers(event)),
                            writers=resultOf(store.writers(event)),
                            reporters=resultOf(store.reporters(event)),
                        ),
                        concentricStreets=resultOf(
                            store.concentricStreets(event)
                        ),
                        incidents=resultOf(store.incidents(event)),
                        incidentReports=resultOf(
                            store.incidentReports(event)
                        ),
                    )
                    for event in resultOf(store.events())
                ),
                incidentTypes=(
                    IncidentType(name=t, hidden=(t not in visibleTypesOut))
                    for t in allTypesOut
                ),
            )

            # Compare imported result to input data
            self.assertIMSDataEqual(imsDataOut, imsDataIn)
