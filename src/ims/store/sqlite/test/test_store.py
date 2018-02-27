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

from .base import TestDataStore
from ...test.base import DataStoreTests as SuperDataStoreTests
from ...test.event import DataStoreEventTests as SuperDataStoreEventTests
from ...test.incident import (
    DataStoreIncidentTests as SuperDataStoreIncidentTests
)
from ...test.report import (
    DataStoreIncidentReportTests as SuperDataStoreIncidentReportTests
)
from ...test.street import (
    DataStoreConcentricStreetTests as SuperDataStoreConcentricStreetTests
)
from ...test.type import (
    DataStoreIncidentTypeTests as SuperDataStoreIncidentTypeTests
)


__all__ = ()



class DataStoreTests(SuperDataStoreTests):
    """
    Parent test class.
    """

    skip = None


    async def store(self) -> TestDataStore:
        store = TestDataStore(self)
        await store.upgradeSchema()
        return store



class DataStoreEventTests(DataStoreTests, SuperDataStoreEventTests):
    """
    Tests for :class:`DataStore` event access.
    """



class DataStoreIncidentTests(DataStoreTests, SuperDataStoreIncidentTests):
    """
    Tests for :class:`DataStore` incident access.
    """



class DataStoreIncidentReportTests(
    DataStoreTests, SuperDataStoreIncidentReportTests
):
    """
    Tests for :class:`DataStore` incident report access.
    """



class DataStoreConcentricStreetTests(
    DataStoreTests, SuperDataStoreConcentricStreetTests
):
    """
    Tests for :class:`DataStore` concentric street access.
    """



class DataStoreIncidentTypeTests(
    DataStoreTests, SuperDataStoreIncidentTypeTests
):
    """
    Tests for :class:`DataStore` incident type access.
    """
