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
from collections.abc import Awaitable, Mapping
from typing import ClassVar, cast
from uuid import uuid4

from attrs import field, frozen, mutable
from docker.api import APIClient
from docker.client import DockerClient
from docker.errors import ImageNotFound, NotFound
from docker.models.containers import Container
from pymysql import OperationalError, ProgrammingError, connect
from pymysql.cursors import DictCursor as Cursor
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.interfaces import IReactorTime
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


@mutable
class DatabaseExistsError(Exception):
    """
    Database already exists.
    """

    name: str


@frozen(kw_only=True)
class MySQLService(ABC):
    """
    MySQL database service.
    """

    _log: ClassVar[Logger] = Logger()

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}("
            + ",".join(
                (
                    f"host={self.host}",
                    f"clientHost={self.clientHost}",
                    f"port={self.port}",
                    f"user={self.user}",
                    "password=<fnord>",
                    "rootPassword=<fnord>",
                )
            )
            + ">"
        )

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

        def sleep(interval: float) -> Deferred[None]:
            d: Deferred[None] = Deferred()
            cast(IReactorTime, reactor).callLater(
                interval, lambda: d.callback(None)
            )
            return d

        error = None
        for _ in range(30):
            try:
                connection = connect(
                    host=self.host,
                    port=self.port,
                    user="root",
                    password=self.rootPassword,
                    cursorclass=Cursor,
                )
            except OperationalError as e:
                self._log.warn("Error creating database: {error}", error=e)
                error = e
                await sleep(1)
            else:
                break
        else:
            assert error is not None
            raise error

        try:
            with connection.cursor() as cursor:
                try:
                    cursor.execute(f"create database {name}")
                except ProgrammingError as e:
                    if e.args[1].endswith("; database exists"):
                        raise DatabaseExistsError(name) from None
                    else:
                        raise
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


@frozen(kw_only=True)
class DockerizedMySQLService(MySQLService):
    """
    Manages a MySQL instance.
    """

    _log: ClassVar[Logger] = Logger()

    @mutable(kw_only=True, eq=False)
    class _State:
        """
        Internal mutable state for :class:`DataStore`.
        """

        container: Deferred[Container] | None = None

        host: str = NO_HOST
        port: int = NO_PORT

        refcount: int = 0

    _user: str = field(factory=randomUserName)
    _password: str = field(factory=randomPassword)
    _rootPassword: str = field(factory=randomPassword)

    _dockerHost: str = "172.17.0.1"

    imageRepository: str = "mysql/mysql-server"
    imageTag: str = "5.6"

    _dockerClient: DockerClient = field(
        factory=DockerClient.from_env, init=False
    )
    _state: _State = field(factory=_State, init=False, repr=False)

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
        d: Deferred[None] = Deferred()

        def waitOnDBStartup(elapsed: float = 0.0) -> None:
            logs = b""

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
                try:
                    logs = container.logs()
                except NotFound:
                    pass
                else:
                    messageBytes = message.encode("latin-1")

                    for line in logs.split(b"\n"):
                        if messageBytes in line:
                            self._log.info(
                                "MySQL container {name} started: {logs}",
                                name=containerName,
                                logs=logs.decode("latin-1"),
                            )
                            d.callback(None)
                            return

                cast(IReactorTime, reactor).callLater(
                    interval, waitOnDBStartup, elapsed=(elapsed + interval)
                )
            except Exception:
                self._log.error(
                    "MySQL container {name} failed to start: {logs}",
                    name=containerName,
                    logs=logs.decode("latin-1"),
                )
                d.errback()

        waitOnDBStartup()

        return d

    def _resetContainerState(self) -> None:
        self._state.host = NO_HOST
        self._state.port = NO_PORT
        self._state.container = None

    async def start(self) -> None:
        self._state.refcount += 1

        self._log.info(
            "Starting MySQL service... (refs={refcount})",
            refcount=self._state.refcount,
        )

        if self._state.container is not None:
            self._log.info("MySQL service has already been started.")
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

            # Get host and port

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

            # Notify that we are ready

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
        self._state.refcount -= 1

        self._log.info(
            "Stopping MySQL service... (refs={refcount})",
            refcount=self._state.refcount,
        )

        if self._state.refcount < 0:
            self._log.critical("MySQL service stopped more times than started.")

        if self._state.refcount == 0:
            self._resetContainerState()
            self._log.info("Stopping MySQL container {name}", name=name)
            container.stop(timeout=0)

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


@frozen(kw_only=True)
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
        return "%"

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
