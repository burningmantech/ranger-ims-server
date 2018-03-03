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

from random import choice
from string import ascii_letters, digits
from typing import Awaitable, Mapping, Optional, cast

from docker.api import APIClient
from docker.client import DockerClient
from docker.errors import ImageNotFound, NotFound
from docker.models.containers import Container

from pymysql import connect
from pymysql.cursors import DictCursor as Cursor
from pymysql.err import MySQLError

from twisted.enterprise.adbapi import ConnectionPool
from twisted.internet import reactor
from twisted.internet.defer import Deferred, ensureDeferred
from twisted.internet.threads import deferToThread
from twisted.logger import Logger

from ims.model import Event, Incident, IncidentReport

from .._store import DataStore
from ...test.base import (
    DataStoreTests as SuperDataStoreTests, TestDataStore as SuperTestDataStore
)


__all__ = ()


def randomString(length: int = 32) -> str:
    """
    Generate a random string.
    """
    return "".join(choice(ascii_letters + digits) for i in range(length))



class DataStoreTests(SuperDataStoreTests):
    """
    Parent test class.
    """

    log = Logger()

    skip: Optional[str] = None

    dbImageRepository = "mysql/mysql-server"
    dbImageTag        = "5.6"
    dbDockerHost      = "172.17.0.1"
    dbRootPassword    = randomString()
    dbUser            = "ims"
    dbPassword        = randomString()


    @classmethod
    def dbContainerName(cls) -> str:
        return "ims-unittest-db-{}".format(id(cls))


    @classmethod
    def dockerClient(cls) -> DockerClient:
        if not hasattr(cls, "_dockerClient"):
            client = DockerClient.from_env()
            cls._dockerClient = client

        return cls._dockerClient


    @classmethod
    def waitOnContainerLog(
        cls, container: Container, message: str,
        timeout: float = 60.0, interval: float = 1.0,
    ) -> Awaitable:
        d = Deferred()

        def waitOnDBStartup(elapsed: float = 0.0) -> None:
            dbContainerName = cls.dbContainerName()

            if elapsed > timeout:
                d.errback(
                    RuntimeError(
                        f"Timed out while starting container {dbContainerName}"
                    )
                )
                return

            cls.log.info(
                "Waiting on container {name} to start...", name=dbContainerName
            )

            # FIXME: We fetch the full logs each time because the streaming API
            # logs(stream=True) blocks.
            logs = container.logs()

            messageBytes = message.encode("latin-1")

            for line in logs.split(b"\n"):
                if messageBytes in line:
                    cls.log.info(
                        "MySQL base container {name} started",
                        name=dbContainerName,
                    )
                    cls.log.info("{logs}", logs=logs.decode("latin-1"))
                    d.callback(logs)
                    return

            reactor.callLater(
                interval, waitOnDBStartup, elapsed=(elapsed + interval)
            )

        waitOnDBStartup()

        return d


    @classmethod
    def dbContainerEnvironment(cls) -> Mapping:
        return dict(
            MYSQL_ROOT_PASSWORD=cls.dbRootPassword,
            # So we can connect as root from the Docker host
            MYSQL_ROOT_HOST=cls.dbDockerHost,
            MYSQL_USER=cls.dbUser,
            MYSQL_PASSWORD=cls.dbPassword,
        )


    @classmethod
    async def startDBContainer(cls) -> Container:
        client = cls.dockerClient()

        try:
            image = client.images.get(
                f"{cls.dbImageRepository}:{cls.dbImageTag}"
            )
        except ImageNotFound:
            cls.log.info("Pulling MySQL image")
            image = await deferToThread(
                client.images.pull, cls.dbImageRepository, cls.dbImageTag
            )

        dbContainerName = cls.dbContainerName()

        cls.log.info(
            "Creating MySQL database container {name}", name=dbContainerName
        )

        container = client.containers.create(
            name=dbContainerName,
            image=image.id,
            auto_remove=True, detach=True,
            environment=cls.dbContainerEnvironment(),
            ports={3306: None},
        )

        cls.log.info(
            "Starting MySQL database container {name}", name=dbContainerName
        )
        container.start()

        try:
            await cls.waitOnContainerLog(container, " starting as process 1 ")

        except Exception as e:
            cls.log.info(
                "Stopping MySQL database container {name} due to error: "
                "{error}",
                name=dbContainerName, error=e,
            )
            container.stop()
            raise

        return container


    @classmethod
    async def dbContainer(cls) -> Container:
        if cls._dbContainer is None:
            d = cls._dbContainer = Deferred()
            d.callback(await cls.startDBContainer())

        container = await cast(Awaitable[Container], cls._dbContainer)

        if not hasattr(cls, "dbHost"):
            apiClient = APIClient()

            port = apiClient.port(container.id, 3306)[0]

            cls.dbHost = port["HostIp"]
            cls.dbPort = int(port["HostPort"])

            dbContainerName = cls.dbContainerName()

            cls.log.info(
                "Database container {name} ready at: {host}:{port}",
                name=dbContainerName, host=cls.dbHost, port=cls.dbPort
            )

            # cls.log.info(
            #     "docker exec"
            #     " --interactive"
            #     " --tty"
            #     " {container}"
            #     " mysql"
            #     " --host=docker.for.mac.host.internal"
            #     " --port={port}"
            #     " --user=root"
            #     " --password={password}"
            #     "",
            #     container=dbContainerName,
            #     port=cls.dbPort,
            #     password=cls.dbRootPassword,
            # )

            # Clean up the container before the reactor shuts down
            reactor.addSystemEventTrigger(
                "before", "shutdown", cls.stopDBContainer
            )

        return container

    _dbContainer: Optional[Awaitable[Container]] = None


    @classmethod
    def stopDBContainer(cls) -> None:
        client = cls.dockerClient()
        dbContainerName = cls.dbContainerName()
        cls.log.info(
            "Stopping MySQL database container {name}", name=dbContainerName
        )
        try:
            container = client.containers.get(dbContainerName)
        except NotFound:
            pass
        else:
            # Set timeout=0 because we don't care about unclean shutdowns
            container.stop(timeout=0)


    def setUp(self) -> None:
        # setUp can't return a coroutine, so this can't be an async method.
        return ensureDeferred(self.dbContainer())


    async def createDatabase(self, name: str) -> None:
        dbContainerName = self.dbContainerName()

        self.log.info(
            "Creating database {name} in container {container}.",
            name=name, container=dbContainerName,
        )

        connection = connect(
            host=self.dbHost,
            port=self.dbPort,
            user="root",
            password=self.dbRootPassword,
            cursorclass=Cursor,
        )

        try:
            with connection.cursor() as cursor:
                cursor.execute(f"create database {name}")
                cursor.execute(
                    f"grant all privileges on {name}.* "
                    "to %(user)s@%(host)s identified by %(password)s",
                    dict(
                        user=self.dbUser,
                        host=self.dbDockerHost,
                        password=self.dbPassword,
                    )
                )

            connection.commit()
        finally:
            connection.close()

        # self.log.info(
        #     "docker exec"
        #     " --interactive"
        #     " --tty"
        #     " {container}"
        #     " mysql"
        #     " --host=docker.for.mac.host.internal"
        #     " --port={port}"
        #     " --user={user}"
        #     " --password={password}"
        #     " --database={database}"
        #     "",
        #     container=dbContainerName,
        #     port=self.dbPort,
        #     user=self.dbUser,
        #     password=self.dbPassword,
        #     database=name,
        # )


    async def store(self) -> "TestDataStore":
        dbName = randomString()

        await self.createDatabase(dbName)

        store = TestDataStore(
            self,
            hostName=self.dbHost,
            hostPort=self.dbPort,
            database=dbName,
            username=self.dbUser,
            password=self.dbPassword,
        )
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
