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

from hypothesis import given

from ims.ext.json import jsonTextFromObject, objectFromJSONText
from ims.ext.trial import TestCase
from ims.model import (
    EventAccess, EventData, IMSData, IncidentType, KnownIncidentType
)
from ims.model.json import jsonObjectFromModelObject, modelObjectFromJSONObject
from ims.model.strategies import imsDatas
from ims.store import IMSDataStore
from ims.store.sqlite import DataStore as SQLiteDataStore

from .._json import JSONExporter, JSONImporter


__all__ = ()


def addKnownIncidentTypes(imsData: IMSData) -> IMSData:
    """
    Add known incident types to imsDataIn, because that's going to be
    expected in the end result, since creating the schema will add them.
    """
    incidentTypesIn = frozenset(imsData.incidentTypes)
    incidentTypesIn |= frozenset(
        IncidentType(name=kt.value, hidden=False)
        for kt in KnownIncidentType
        if kt.value not in (t.name for t in incidentTypesIn)
    )
    return imsData.replace(incidentTypes=incidentTypesIn)



class JSONExporterTests(TestCase):
    """
    Tests for :class:`JSONExporter`
    """

    def store(self, imsData: IMSData) -> IMSDataStore:
        store = SQLiteDataStore(dbPath=Path(self.mktemp()))
        self.successResultOf(store.upgradeSchema())

        importer = JSONImporter(store=store, imsData=imsData)
        self.successResultOf(importer.storeData())

        return store


    @given(imsDatas())
    def test_asBytes(self, imsDataIn: IMSData) -> None:
        imsDataIn = addKnownIncidentTypes(imsDataIn)

        # Create a new data store and import imsDataIn into it
        store = self.store(imsData=imsDataIn)

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

        # Create a new data store and import imsDataIn into it
        store = self.store(imsData=imsDataIn)

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

        # Create a new data store and import imsDataIn into it
        store = self.store(imsData=imsDataIn)

        # Export the data from that store
        exporter = JSONExporter(store=store)
        json = self.successResultOf(exporter.asJSON())
        imsDataOut = modelObjectFromJSONObject(json, IMSData)

        # Compare result to input data
        self.assertIMSDataEqual(imsDataOut, imsDataIn)


    @given(imsDatas())
    def test_imsData(self, imsDataIn: IMSData) -> None:
        imsDataIn = addKnownIncidentTypes(imsDataIn)

        # Create a new data store and import imsDataIn into it
        store = self.store(imsData=imsDataIn)

        # Export the data from that store
        exporter = JSONExporter(store=store)
        imsDataOut = self.successResultOf(exporter.imsData())

        # Compare exported result to input data
        self.assertIMSDataEqual(imsDataOut, imsDataIn)



class JSONImporterTests(TestCase):
    """
    Tests for :class:`JSONImporter`
    """

    def store(self) -> IMSDataStore:
        store = SQLiteDataStore(dbPath=Path(self.mktemp()))
        self.successResultOf(store.upgradeSchema())
        return store


    @given(imsDatas())
    def test_fromIO(self, imsDataIn: IMSData) -> None:
        json = jsonObjectFromModelObject(imsDataIn)
        jsonText = jsonTextFromObject(json)
        jsonBytes = jsonText.encode("utf-8")
        jsonIO = BytesIO(jsonBytes)
        importer = JSONImporter.fromIO(store=self.store(), io=jsonIO)

        self.assertIMSDataEqual(importer.imsData, imsDataIn)


    @given(imsDatas())
    def test_fromBytes(self, imsDataIn: IMSData) -> None:
        json = jsonObjectFromModelObject(imsDataIn)
        jsonText = jsonTextFromObject(json)
        jsonBytes = jsonText.encode("utf-8")
        importer = JSONImporter.fromBytes(
            store=self.store(), jsonBytes=jsonBytes
        )

        self.assertIMSDataEqual(importer.imsData, imsDataIn)


    @given(imsDatas())
    def test_fromText(self, imsDataIn: IMSData) -> None:
        json = jsonObjectFromModelObject(imsDataIn)
        jsonText = jsonTextFromObject(json)
        importer = JSONImporter.fromText(store=self.store(), jsonText=jsonText)

        self.assertIMSDataEqual(importer.imsData, imsDataIn)


    @given(imsDatas())
    def test_fromJSON(self, imsDataIn: IMSData) -> None:
        json = jsonObjectFromModelObject(imsDataIn)
        importer = JSONImporter.fromJSON(store=self.store(), json=json)

        self.assertIMSDataEqual(importer.imsData, imsDataIn)


    @given(imsDatas())
    def test_storeData(self, imsDataIn: IMSData) -> None:
        imsDataIn = addKnownIncidentTypes(imsDataIn)

        resultOf = self.successResultOf

        # Create a new data store and import imsDataIn into it
        store = self.store()
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
