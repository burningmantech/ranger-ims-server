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

from typing import Mapping, Optional, cast

from docker.client import DockerClient
from docker.errors import NotFound
from docker.models.containers import Container

from twisted.enterprise.adbapi import ConnectionPool
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.logger import Logger

from ims.model import Event, Incident, IncidentReport

from .._store import DataStore
from ...test.base import (
    DataStoreTests as SuperDataStoreTests, TestDataStore as SuperTestDataStore
)


__all__ = ()



class DataStoreTests(SuperDataStoreTests):
    """
    Parent test class.
    """

    log = Logger()

    skip: Optional[str] = None

    dbContainerImageName = "mysql/mysql-server"
    dbContainerImageTag  = "5.6"

    dbName     = "imsdb"
    dbUser     = "imsuser"
    dbPassword = "imspassword"


    @classmethod
    def dbEnvironment(cls) -> Mapping:
        return dict(
            MYSQL_RANDOM_ROOT_PASSWORD="yes",
            MYSQL_DATABASE=cls.dbName,
            MYSQL_USER=cls.dbUser,
            MYSQL_PASSWORD=cls.dbPassword,
        )


    @property
    def dbContainer(self) -> None:
        if not hasattr(self, "_dbContainer"):
            self.log.info("Creating database container")

            client = DockerClient.from_env()
            container = client.containers.create(
                image=(
                    f"{self.dbContainerImageName}:{self.dbContainerImageTag}"
                ),
                auto_remove=True, detach=True,
            )

            self._dbContainer = container

        return self._dbContainer


    def setUp(self) -> None:
        container = self.dbContainer
        self.log.info("Starting database container")
        container.start()

        d = Deferred()

        interval = 1.0
        timeout = 10.0

        def waitOnDBStartup(elapsed=0.0):
            if elapsed > timeout:
                d.errback(
                    RuntimeError("Unable to start test database.")
                )

            self.log.info("Waiting on database container to start MySQL...")

            # FIXME: We fetch the full logs each time because the streaming API
            # logs(stream=True) blocks.
            logs = container.logs()

            for line in logs.split(b"\n"):
                if b" Starting MySQL " in line:
                    self.log.info("Test database started: {line}", line=line)
                    d.callback(None)
                    return

            reactor.callLater(
                interval, waitOnDBStartup, elapsed=elapsed+interval
            )

        waitOnDBStartup()

        return d


    def tearDown(self) -> None:
        container = self.dbContainer

        self.log.info("Stopping database container")
        # Since we're going to remove the container anyway, we don't care about
        # it getting a chance to clean up, so set timeout=0.
        container.stop(timeout=0)


    def store(self) -> "TestDataStore":
        return TestDataStore(
            self,
            hostname="localhost",
            database=self.dbName,
            username=self.dbUser,
            password=self.dbPassword,
        )



class TestDataStore(SuperTestDataStore, DataStore):
    """
    See :class:`SuperTestDataStore`.
    """

    maxIncidentNumber = 4294967295

    exceptionClass = RuntimeError


    def __init__(
        self, testCase: DataStoreTests,
        hostname: str,
        database: str,
        username: str,
        password: str,
    ) -> None:
        DataStore.__init__(
            self,
            hostname=hostname, database=database,
            username=username, password=password,
        )
        setattr(self._state, "testCase", testCase)


    @property
    def _db(self) -> ConnectionPool:
        if getattr(self._state, "broken", False):
            self.raiseException()

        return cast(property, DataStore._db).fget(self)


    def bringThePain(self) -> None:
        setattr(self._state, "broken", True)
        assert getattr(self._state, "broken")


    def storeEvent(self, event: Event) -> None:
        raise NotImplementedError()


    def storeIncident(self, incident: Incident) -> None:
        raise NotImplementedError()


    def storeIncidentReport(
        self, incidentReport: IncidentReport
    ) -> None:
        raise NotImplementedError()


    def storeConcentricStreet(
        self, event: Event, streetID: str, streetName: str,
        ignoreDuplicates: bool = False,
    ) -> None:
        raise NotImplementedError()


    def storeIncidentType(self, name: str, hidden: bool) -> None:
        raise NotImplementedError()


    @staticmethod
    def normalizeIncidentAddress(incident: Incident) -> Incident:
        raise NotImplementedError()
