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

from typing import Awaitable, Mapping, Optional, cast

from docker.api import APIClient
from docker.client import DockerClient
from docker.errors import ImageNotFound, NotFound
from docker.models.containers import Container
from docker.models.images import Image

from pymysql.err import MySQLError

from twisted.enterprise.adbapi import ConnectionPool
from twisted.internet import reactor
from twisted.internet.defer import Deferred, ensureDeferred
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

    mysqlImageName     = "mysql/mysql-server"
    mysqlImageTag      = "5.6"
    mysqlContainerName = "ims-unittest-mysql"

    dbContainerName = "ims-unittest-db"
    dbImageName     = "ims-unittest-mysql5.6"
    dbImageTag      = 0  # str(DataStore.schemaVersion)

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


    @classmethod
    def dockerClient(cls) -> DockerClient:
        if not hasattr(cls, "_dockerClient"):
            client = DockerClient.from_env()
            cls._dockerClient = client

        return cls._dockerClient


    @classmethod
    def _createMySQLContainer(cls) -> Container:
        cls.log.info("Creating MySQL base container")

        client = cls.dockerClient()
        container = client.containers.create(
            name=f"{cls.mysqlContainerName}",
            image=f"{cls.mysqlImageName}:{cls.mysqlImageTag}",
            auto_remove=True, detach=True,
            environment={
                "MYSQL_RANDOM_ROOT_PASSWORD": "yes",
                "MYSQL_DATABASE": cls.dbName,
                "MYSQL_USER": cls.dbUser,
                "MYSQL_PASSWORD": cls.dbPassword,
            }
        )

        return container


    @classmethod
    def _waitOnContainerLog(
        cls, container: Container, message: str,
        timeout: float = 60.0, interval: float = 1.0,
    ) -> Awaitable:
        d = Deferred()

        def waitOnDBStartup(elapsed: float = 0.0) -> None:
            if elapsed > timeout:
                d.errback(
                    RuntimeError("Timed out while starting container")
                )
                return

            cls.log.info("Waiting on container to start...")

            # FIXME: We fetch the full logs each time because the streaming API
            # logs(stream=True) blocks.
            logs = container.logs()

            messageBytes = message.encode("latin-1")

            for line in logs.split(b"\n"):
                if messageBytes in line:
                    cls.log.info("MySQL base container started")
                    cls.log.info("{logs}", logs=logs.decode("latin-1"))
                    d.callback(None)
                    return

            reactor.callLater(
                interval, waitOnDBStartup, elapsed=(elapsed + interval)
            )

        waitOnDBStartup()

        return d


    @classmethod
    async def _startMySQLContainer(cls, container: Container) -> None:
        cls.log.info("Starting MySQL base container")
        container.start()

        await cls._waitOnContainerLog(container, " starting as process 1 ")


    @classmethod
    async def _createDBImage(cls) -> None:
        container = cls._createMySQLContainer()

        await cls._startMySQLContainer(container)

        cls.log.info(
            "Committing MySQL base container to database container image"
        )
        container.commit(cls.dbImageName, cls.dbImageTag)

        cls.log.info("Stopping MySQL base container")
        container.stop()


    @classmethod
    async def _dbImage(cls) -> Image:
        client = cls.dockerClient()

        imageName = f"{cls.dbImageName}:{cls.dbImageTag}"

        try:
            image = client.images.get(imageName)
        except ImageNotFound:
            if cls._creatingDBImage is None:
                cls._creatingDBImage = cls._createDBImage()

            await cls._creatingDBImage

            image = client.images.get(imageName)

        return image

    _creatingDBImage: Optional[Awaitable] = None


    @classmethod
    async def _startDBContainer(cls) -> Container:
        image = await cls._dbImage()

        cls.log.info("Creating MySQL database container")

        client = cls.dockerClient()
        container = client.containers.create(
            name=f"{cls.dbContainerName}",
            image=image.id, auto_remove=True, detach=True,
            ports={3306: None},
        )

        cls.log.info("Starting MySQL database container")
        container.start()

        try:
            await cls._waitOnContainerLog(container, " starting as process 1 ")

        except Exception as e:
            cls.log.info(
                "Stopping MySQL database container due to error: {error}",
                error=e,
            )
            container.stop()
            raise

        return container


    @classmethod
    async def dbContainer(cls) -> Container:
        client = cls.dockerClient()

        try:
            container = client.containers.get(cls.dbContainerName)
        except NotFound:
            if cls._dbContainer is None:
                cls._dbContainer = cls._startDBContainer()

            container = await cls._dbContainer

        if not hasattr(cls, "dbHost"):
            apiClient = APIClient()

            port = apiClient.port(container.id, 3306)[0]

            cls.dbHost = port["HostIp"]
            cls.dbPort = int(port["HostPort"])

            cls.log.info(
                f"Database ready. To connect:"
                f" docker run"
                f" --rm"
                f" --interactive"
                f" --tty"
                f" {cls.mysqlImageName}:{cls.mysqlImageTag}"
                f" mysql"
                f" --host=docker.for.mac.host.internal"
                f" --port={cls.dbPort}"
                f" --database={cls.dbName}"
                f" --user={cls.dbUser}"
                f" --password={cls.dbPassword}"
            )

            # Clean up the container before the reactor shuts down
            from twisted.internet import reactor
            reactor.addSystemEventTrigger(
                "before", "shutdown", cls.stopDBContainer
            )

        return container

    _dbContainer: Optional[Awaitable] = None


    @classmethod
    def stopDBContainer(cls) -> None:
        client = cls.dockerClient()
        try:
            cls.log.info("Stopping MySQL database container")
            container = client.containers.get(cls.dbContainerName)
        except NotFound:
            pass
        container.stop()


    def setUp(self) -> None:
        # setUp can't return a coroutine, so this can't be an async method.
        return ensureDeferred(self.dbContainer())


    async def store(self) -> "TestDataStore":
        store = TestDataStore(
            self,
            hostName=self.dbHost,
            hostPort=self.dbPort,
            database=self.dbName,
            username=self.dbUser,
            password=self.dbPassword,
        )
        await store.resetDatabase()
        await store.upgradeSchema()
        return store



class TestDataStore(SuperTestDataStore, DataStore):
    """
    See :class:`SuperTestDataStore`.
    """

    maxIncidentNumber = 4294967295

    exceptionClass = MySQLError


    def __init__(
        self, testCase: DataStoreTests,
        hostName: str,
        hostPort: int,
        database: str,
        username: str,
        password: str,
    ) -> None:
        DataStore.__init__(
            self,
            hostName=hostName, hostPort=hostPort,
            database=database,
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


    async def storeEvent(self, event: Event) -> None:
        await self._db.runOperation(
            "insert into EVENT (NAME) values (%(eventID)s)",
            dict(eventID=event.id)
        )


    async def storeIncident(self, incident: Incident) -> None:
        raise NotImplementedError("storeIncident()")


    async def storeIncidentReport(
        self, incidentReport: IncidentReport
    ) -> None:
        raise NotImplementedError("storeIncidentReport()")


    async def storeConcentricStreet(
        self, event: Event, streetID: str, streetName: str,
        ignoreDuplicates: bool = False,
    ) -> None:
        if ignoreDuplicates:
            ignore = " or ignore"
        else:
            ignore = ""

        await self._db.runOperation(
            f"""
            insert{ignore} into CONCENTRIC_STREET (EVENT, ID, NAME)
            values (
                (select ID from EVENT where NAME = %(eventID)s),
                %(streetID)s,
                %(streetName)s
            )
            """,
            dict(
                eventID=event.id, streetID=streetID, streetName=streetName
            )
        )


    async def storeIncidentType(self, name: str, hidden: bool) -> None:
        await self._db.runQuery(
            "insert into INCIDENT_TYPE (NAME, HIDDEN) "
            "values (%(name)s, %(hidden)s)",
            dict(name=name, hidden=hidden)
        )


    @staticmethod
    def normalizeIncidentAddress(incident: Incident) -> Incident:
        raise NotImplementedError("normalizeIncidentAddress()")
