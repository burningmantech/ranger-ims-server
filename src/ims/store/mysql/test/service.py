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
Start up a MySQL service for testing.
This implementation uses Docker containers.
"""

from abc import ABC, abstractmethod
from typing import Awaitable, ClassVar, Mapping, Optional, cast
from uuid import uuid4

from attr import Factory, attrib, attrs

from docker.api import APIClient
from docker.client import DockerClient
from docker.errors import ImageNotFound
from docker.models.containers import Container

from pymysql import connect
from pymysql.cursors import DictCursor as Cursor

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.threads import deferToThread
from twisted.logger import Logger


__all__ = ()


def randomDatabaseName() -> str:
    """
    Generate a unique string for use as a database name.
    """
    return f"d{uuid4().hex}"


def randomUserName() -> str:
    """
    Generate a unique string for use as a database name.
    """
    return f"u{uuid4().hex}"[:16]


def randomPassword() -> str:
    """
    Generate a unique string for use as a database name.
    """
    return f"p{uuid4().hex}"


NO_HOST = ""
NO_PORT = 0


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class MySQLService(ABC):
    """
    MySQL database service.
    """

    _log: ClassVar[Logger] = Logger()

    @property
    @abstractmethod
    def host(self) -> str:
        """
        Server network address host name.
        """

    @property
    @abstractmethod
    def clientHost(self) -> str:
        """
        Client host name to use in grant statements.
        """

    @property
    @abstractmethod
    def port(self) -> int:
        """
        Server network address port number.
        """

    @property
    @abstractmethod
    def user(self) -> str:
        """
        Database user name.
        """

    @property
    @abstractmethod
    def password(self) -> str:
        """
        Database user password.
        """

    @property
    @abstractmethod
    def rootPassword(self) -> str:
        """
        Server root user password.
        """

    @abstractmethod
    async def start(self) -> None:
        """
        Start the service.
        """

    @abstractmethod
    async def stop(self) -> None:
        """
        Stop the service.
        """

    async def createDatabase(self, name: str) -> None:
        """
        Create a database.
        """
        self._log.info(
            "Creating database {name} in MySQL service {service}.",
            name=name,
            service=self,
        )

        connection = connect(
            host=self.host,
            port=self.port,
            user="root",
            password=self.rootPassword,
            cursorclass=Cursor,
        )

        try:
            with connection.cursor() as cursor:
                cursor.execute(f"create database {name}")
                cursor.execute(
                    f"grant all privileges on {name}.* "
                    f"to %(user)s@%(host)s identified by %(password)s",
                    dict(
                        user=self.user,
                        host=self.clientHost,
                        password=self.password,
                    ),
                )

            connection.commit()
        finally:
            connection.close()


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class DockerizedMySQLService(MySQLService):
    """
    Manages a MySQL instance.
    """

    _log: ClassVar[Logger] = Logger()

    @attrs(frozen=False, auto_attribs=True, kw_only=True, eq=False)
    class _State(object):
        """
        Internal mutable state for :class:`DataStore`.
        """

        container: Optional[Deferred] = None

        host = NO_HOST
        port = NO_PORT

    _user: str = Factory(randomUserName)
    _password: str = Factory(randomPassword)
    _rootPassword: str = Factory(randomPassword)

    _dockerHost: str = "172.17.0.1"

    imageRepository = "mysql/mysql-server"
    imageTag = "5.6"

    _dockerClient: DockerClient = attrib(
        factory=DockerClient.from_env, init=False
    )
    _state: _State = attrib(factory=_State, init=False)

    @property
    def host(self) -> str:
        return self._state.host

    @property
    def clientHost(self) -> str:
        return self._dockerHost

    @property
    def port(self) -> int:
        return self._state.port

    @property
    def user(self) -> str:
        return self._user

    @property
    def password(self) -> str:
        return self._password

    @property
    def rootPassword(self) -> str:
        return self._rootPassword

    @property
    def _containerName(self) -> str:
        cid = id(self)
        return f"MySQLService-{cid}"

    @property
    def _containerEnvironment(self) -> Mapping[str, str]:
        return dict(
            # Set root password so that we can connect as root from the Docker
            # host for debugging
            MYSQL_ROOT_PASSWORD=self.rootPassword,
            MYSQL_ROOT_HOST=self._dockerHost,
            MYSQL_USER=self.user,
            MYSQL_PASSWORD=self.password,
        )

    def _waitOnContainerLog(
        self,
        container: Container,
        message: str,
        timeout: float = 60.0,
        interval: float = 1.0,
    ) -> Awaitable[None]:
        lastLogs = [b""]

        d = Deferred()

        def waitOnDBStartup(elapsed: float = 0.0) -> None:
            try:
                containerName = self._containerName

                if elapsed > timeout:
                    d.errback(
                        RuntimeError(
                            f"Timed out while starting container "
                            f"{containerName}"
                        )
                    )
                    return

                self._log.info(
                    "Waiting on MySQL container {name} to start...",
                    name=containerName,
                )

                # FIXME: We fetch the full logs each time because the streaming
                # API logs(stream=True) blocks.
                logs = container.logs()

                messageBytes = message.encode("latin-1")

                for line in logs.split(b"\n"):
                    if messageBytes in line:
                        self._log.info(
                            "MySQL container {name} started",
                            name=containerName,
                        )
                        self._log.info("{logs}", logs=logs.decode("latin-1"))
                        d.callback(logs)
                        return

                lastLogs[0] = logs

                reactor.callLater(
                    interval, waitOnDBStartup, elapsed=(elapsed + interval)
                )
            except Exception as e:
                self._log.error(
                    "Last seen log output:\n{log}",
                    log=lastLogs[0].decode("utf-8"),
                )
                d.errback(e)

        waitOnDBStartup()

        return cast(Awaitable[None], d)

    def _resetContainerState(self) -> None:
        self._state.host = NO_HOST
        self._state.port = NO_PORT
        self._state.container = None

    async def start(self) -> None:
        if self._state.container is not None:
            # Already started or starting
            await self._state.container
            return

        self._state.container = Deferred()

        client = self._dockerClient

        imageName = f"{self.imageRepository}:{self.imageTag}"

        try:
            image = client.images.get(imageName)
        except ImageNotFound:
            self._log.info("Pulling MySQL image: {name}", name=imageName)
            image = await deferToThread(
                client.images.pull, self.imageRepository, self.imageTag
            )

        containerName = self._containerName

        self._log.info("Creating MySQL container {name}", name=containerName)
        self._log.info(
            "Container environment: {env}", env=self._containerEnvironment
        )

        container = client.containers.create(
            name=containerName,
            image=image.id,
            auto_remove=True,
            detach=True,
            environment=self._containerEnvironment,
            ports={3306: None},
        )

        self._log.info("Starting MySQL container {name}", name=containerName)
        container.start()

        try:
            await self._waitOnContainerLog(container, " starting as process 1 ")

            # Clean up the container before the reactor shuts down
            reactor.addSystemEventTrigger(
                "before",
                "shutdown",
                lambda: self._stop(container, containerName),
            )

            apiClient = APIClient()

            netloc = apiClient.port(container.id, 3306)[0]

            self._state.host = netloc["HostIp"]
            self._state.port = int(netloc["HostPort"])

            self._log.info(
                "MySQL container {name} ready at: {host}:{port}",
                name=containerName,
                host=self.host,
                port=self.port,
            )

            self._log.info(
                "To connect to MySQL, run:\n"
                "docker exec"
                " --interactive"
                " --tty"
                " {container}"
                " mysql"
                " --host=docker.for.mac.host.internal"
                " --port={port}"
                " --user=root"
                " --password={password}"
                "",
                container=containerName,
                port=self.port,
                password=self.rootPassword,
            )

            self._state.container.callback(container)

        except Exception as e:
            self._resetContainerState()
            self._log.failure(
                "Stopping MySQL container {name} due to error: {error}",
                name=containerName,
                error=e,
            )
            container.stop()
            raise

    def _stop(self, container: Container, name: str) -> None:
        self._log.info("Stopping MySQL container {name}", name=name)
        container.stop(timeout=0)
        self._resetContainerState()

    async def stop(self) -> None:
        if self._state.container is None:
            # Not running
            return

        container = await self._state.container

        self._stop(container, self._containerName)

    async def createDatabase(self, name: str) -> None:
        await super().createDatabase(name)

        self._log.info(
            "docker exec"
            " --interactive"
            " --tty"
            " {container}"
            " mysql"
            " --host=docker.for.mac.host.internal"
            " --port={port}"
            " --user={user}"
            " --password={password}"
            " --database={database}"
            "",
            container=self._containerName,
            port=self.port,
            user=self.user,
            password=self.password,
            database=name,
        )


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class ExternalMySQLService(MySQLService):
    """
    Externally hosted MySQL instance.
    """

    _log: ClassVar[Logger] = Logger()

    _host: str
    _port: int
    _user: str
    _password: str
    _rootPassword: str

    @property
    def host(self) -> str:
        return self._host

    @property
    def clientHost(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @property
    def user(self) -> str:
        return self._user

    @property
    def password(self) -> str:
        return self._password

    @property
    def rootPassword(self) -> str:
        return self._rootPassword

    async def start(self) -> None:
        """
        Start the service.
        """

    async def stop(self) -> None:
        """
        Stop the service.
        """
        raise RuntimeError("Can't stop external MySQL service")
