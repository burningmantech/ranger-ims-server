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
IMS configuration
"""

from collections.abc import Callable, Sequence
from configparser import ConfigParser, NoOptionError, NoSectionError
from datetime import timedelta as TimeDelta
from functools import partial
from os import environ, getcwd
from os.path import basename
from pathlib import Path
from sys import argv
from typing import Any, ClassVar, cast

from attr import Factory, evolve
from attrs import field, frozen, mutable
from twisted.logger import Logger

from ims.auth import AuthProvider
from ims.directory import IMSDirectory
from ims.directory.clubhouse_db import DMSDirectory, DutyManagementSystem
from ims.directory.file import FileDirectory
from ims.ext.enum import Enum, Names, auto
from ims.store import IMSDataStore
from ims.store.mysql import DataStore as MySQLDataStore
from ims.store.sqlite import DataStore as SQLiteDataStore

from ._urls import URLs


__all__ = ()


def describeFactory(f: Callable[..., Any]) -> str:
    if isinstance(f, partial):
        if "password" in f.keywords:
            keywords = dict(f.keywords)
            keywords["password"] = "(REDACTED)"  # nosec
        else:
            keywords = f.keywords

        result = [f"{a!r}" for a in f.args]
        result.extend(f"{k}={v!r}" for k, v in keywords.items())
        args = ", ".join(result)
        return f"{f.func.__name__}({args})"

    else:
        return f"{f.__name__}(...)"


@mutable
class ConfigurationError(Exception):
    """
    Configuration error.
    """

    message: str


class LogFormat(Names):
    """
    Log formats.
    """

    text = auto()
    json = auto()


@frozen(kw_only=True)
class ConfigFileParser:
    """
    Configuration parser.
    """

    _log: ClassVar[Logger] = Logger()

    path: Path | None
    _configParser: ConfigParser = Factory(ConfigParser)

    def __attrs_post_init__(self) -> None:
        if self.path is None:
            self._log.info("No configuration file specified.")
            return

        for _okFile in self._configParser.read(str(self.path)):
            self._log.info("Read configuration file: {path}", path=self.path)
            break
        else:
            self._log.error(
                "Unable to read configuration file: {path}",
                path=self.path,
            )

    def valueFromConfig(
        self, variable: str, section: str, option: str, default: str = ""
    ) -> str:
        value = environ.get(f"IMS_{variable}")

        if not value:
            try:
                value = self._configParser.get(section, option)
            except (NoSectionError, NoOptionError):
                pass

        if value:
            return value
        else:
            return default

    def pathFromConfig(
        self,
        variable: str,
        section: str,
        option: str,
        root: Path,
        segments: Sequence[str],
    ) -> Path:
        text = self.valueFromConfig(variable, section, option)

        if text:
            path = Path(text)
        else:
            path = root.resolve().joinpath(*segments)

        if not path.is_absolute():
            path = root.resolve() / path

        return path

    def enumFromConfig(
        self,
        variable: str,
        section: str,
        option: str,
        default: Enum,
    ) -> Enum:
        name = self.valueFromConfig(variable, section, option)

        if not name:
            return default

        try:
            return type(default)[name]
        except KeyError as e:
            raise ConfigurationError(
                f"Invalid option {name!r} for {section}.{option}"
            ) from e


@frozen(kw_only=True)
class Configuration:
    """
    Configuration
    """

    _log: ClassVar[Logger] = Logger()
    urls: ClassVar = URLs

    @mutable(kw_only=True, eq=False)
    class _State:
        """
        Internal mutable state for :class:`Configuration`.
        """

        store: IMSDataStore | None = None
        directory: IMSDirectory | None = None
        authProvider: AuthProvider | None = None

    @classmethod
    def fromConfigFile(cls, configFile: Path | None) -> "Configuration":
        """
        Load the configuration.
        """
        command = basename(argv[0])

        parser = ConfigFileParser(path=configFile)

        if configFile is None:
            defaultRoot = Path(getcwd())
        else:
            defaultRoot = configFile.parent.parent

        hostName = parser.valueFromConfig(
            "HOSTNAME", "Core", "Host", "localhost"
        )
        cls._log.info("hostName: {hostName}", hostName=hostName)

        port = int(parser.valueFromConfig("PORT", "Core", "Port", "80"))
        cls._log.info("Port: {port}", port=port)

        serverRoot = parser.pathFromConfig(
            "SERVER_ROOT",
            "Core",
            "ServerRoot",
            defaultRoot,
            (),
        )
        serverRoot.mkdir(exist_ok=True)
        cls._log.info("Server root: {path}", path=serverRoot)

        configRoot = parser.pathFromConfig(
            "CONFIG_ROOT", "Core", "ConfigRoot", serverRoot, ("conf",)
        )
        cls._log.info("Config root: {path}", path=configRoot)

        dataRoot = parser.pathFromConfig(
            "DATA_ROOT", "Core", "DataRoot", serverRoot, ("data",)
        )
        dataRoot.mkdir(exist_ok=True)
        cls._log.info("Data root: {path}", path=dataRoot)

        cachedResourcesRoot = parser.pathFromConfig(
            "CACHE_PATH", "Core", "CachedResources", dataRoot, ("cache",)
        )
        cachedResourcesRoot.mkdir(exist_ok=True)
        cls._log.info("CachedResources: {path}", path=cachedResourcesRoot)

        logLevelName = parser.valueFromConfig(
            "LOG_LEVEL", "Core", "LogLevel", "info"
        )
        cls._log.info("LogLevel: {logLevel}", logLevel=logLevelName)

        logFormat = cast(
            LogFormat,
            parser.enumFromConfig(
                "LOG_FORMAT", "Core", "LogFormat", LogFormat.text
            ),
        )
        cls._log.info("LogFormat: {logFormat}", logFormat=logFormat)

        logFilePath = parser.pathFromConfig(
            "LOG_FILE", "Core", "LogFile", dataRoot, (f"{command}.log",)
        )
        cls._log.info("LogFile: {path}", path=logFilePath)

        admins = parser.valueFromConfig("ADMINS", "Core", "Admins")
        imsAdmins: frozenset[str] = frozenset(
            a for a in map(str.strip, admins.split(",")) if a
        )
        cls._log.info("Admins: {admins}", admins=tuple(imsAdmins))

        active = parser.valueFromConfig(
            "REQUIRE_ACTIVE", "Core", "RequireActive", "true"
        )
        active = active.lower()
        if active in ("false", "no", "0"):
            requireActive = False
        else:
            requireActive = True
        cls._log.info("RequireActive: {active}", active=requireActive)

        storeType = parser.valueFromConfig(
            "DATA_STORE", "Core", "DataStore", "SQLite"
        )
        cls._log.info("DataStore: {storeType}", storeType=storeType)

        storeFactory: Callable[[], IMSDataStore]

        if storeType == "SQLite":
            dbPath = parser.pathFromConfig(
                "DB_PATH", "Store:SQLite", "File", dataRoot, ("db.sqlite",)
            )
            cls._log.info("Database: {path}", path=dbPath)

            storeFactory = partial(SQLiteDataStore, dbPath=dbPath)

        elif storeType == "MySQL":
            storeHost = parser.valueFromConfig(
                "DB_HOST_NAME", "Store:MySQL", "HostName", "localhost"
            )
            storePort = int(
                parser.valueFromConfig(
                    "DB_HOST_PORT", "Store:MySQL", "HostPort", "3306"
                )
            )
            storeDatabase = parser.valueFromConfig(
                "DB_DATABASE", "Store:MySQL", "Database"
            )
            storeUser = parser.valueFromConfig(
                "DB_USER_NAME", "Store:MySQL", "UserName"
            )
            storePassword = parser.valueFromConfig(
                "DB_PASSWORD", "Store:MySQL", "Password"
            )
            cls._log.info(
                "Database: {user}@{host}:{port}/{db}",
                user=storeUser,
                host=storeHost,
                port=storePort,
                db=storeDatabase,
            )

            storeFactory = partial(
                MySQLDataStore,
                hostName=storeHost,
                hostPort=storePort,
                database=storeDatabase,
                username=storeUser,
                password=storePassword,
            )

        else:
            raise ConfigurationError(f"Unknown data store: {storeType!r}")

        directoryType = parser.valueFromConfig(
            "DIRECTORY", "Core", "Directory", "File"
        )
        cls._log.info("DataStore: {storeType}", storeType=storeType)

        directory: IMSDirectory

        if directoryType == "File":
            directoryFilePath = parser.pathFromConfig(
                "DIRECTORY_FILE",
                "Directory:File",
                "DirectoryFile",
                configRoot,
                ("directory.yaml",),
            )
            cls._log.info("Directory File: {path}", path=directoryFilePath)

            directory = FileDirectory(path=directoryFilePath)

        elif directoryType == "ClubhouseDB":
            dmsHost = parser.valueFromConfig(
                "DMS_HOSTNAME", "Directory:ClubhouseDB", "Hostname"
            )
            dmsDatabase = parser.valueFromConfig(
                "DMS_DATABASE", "Directory:ClubhouseDB", "Database"
            )
            dmsUsername = parser.valueFromConfig(
                "DMS_USERNAME", "Directory:ClubhouseDB", "Username"
            )
            dmsPassword = parser.valueFromConfig(
                "DMS_PASSWORD", "Directory:ClubhouseDB", "Password"
            )
            dmsCacheInterval = int(
                parser.valueFromConfig(
                    "DMS_CACHE_INTERVAL",
                    "Directory:ClubhouseDB",
                    "CacheInterval",
                    "5",
                )
            )

            cls._log.info(
                "DMS: {user}@{host}/{db}",
                user=dmsUsername,
                host=dmsHost,
                db=dmsDatabase,
            )

            dms = DutyManagementSystem(
                host=dmsHost,
                database=dmsDatabase,
                username=dmsUsername,
                password=dmsPassword,
                cacheInterval=dmsCacheInterval,
            )

            directory = DMSDirectory(dms=dms)

        else:
            raise ConfigurationError(f"Unknown directory: {directoryType!r}")

        masterKey = parser.valueFromConfig("MASTER_KEY", "Core", "MasterKey")

        tokenLifetimeNormal = TimeDelta(
            seconds=int(
                parser.valueFromConfig(
                    "TOKEN_LIFETIME_NORMAL",
                    "Core",
                    "TokenLifetime",
                    str(1 * 60 * 60),
                )
            )
        )
        tokenLifetimeExtended = TimeDelta(
            seconds=int(
                parser.valueFromConfig(
                    "TOKEN_LIFETIME_EXTENDED",
                    "Core",
                    "TokenLifetime",
                    str(30 * 24 * 60 * 60),
                )
            )
        )

        #
        # Persist some objects
        #

        return cls(
            configFile=configFile,
            cachedResourcesRoot=cachedResourcesRoot,
            configRoot=configRoot,
            dataRoot=dataRoot,
            directory=directory,
            hostName=hostName,
            imsAdmins=imsAdmins,
            logFilePath=logFilePath,
            logFormat=logFormat,
            logLevelName=logLevelName,
            masterKey=masterKey,
            tokenLifetimeNormal=tokenLifetimeNormal,
            tokenLifetimeExtended=tokenLifetimeExtended,
            port=port,
            requireActive=requireActive,
            serverRoot=serverRoot,
            storeFactory=storeFactory,
        )

    configFile: Path | None

    cachedResourcesRoot: Path
    configRoot: Path
    dataRoot: Path
    directory: IMSDirectory
    hostName: str
    imsAdmins: frozenset[str]
    logFilePath: Path
    logFormat: LogFormat
    logLevelName: str
    masterKey: str
    tokenLifetimeNormal: TimeDelta
    tokenLifetimeExtended: TimeDelta
    port: int
    requireActive: bool
    serverRoot: Path

    _storeFactory: Callable[[], IMSDataStore]

    _state: _State = field(factory=_State, init=False, repr=False)

    @property
    def store(self) -> IMSDataStore:
        """
        Data store.
        """
        if self._state.store is None:
            self._state.store = self._storeFactory()

        return self._state.store

    @property
    def authProvider(self) -> AuthProvider:
        """
        Auth provider.
        """
        if self._state.authProvider is None:
            self._state.authProvider = AuthProvider(
                store=self.store,
                directory=self.directory,
                requireActive=self.requireActive,
                adminUsers=self.imsAdmins,
                masterKey=self.masterKey,
            )

        return self._state.authProvider

    def __str__(self) -> str:
        return (
            f"Configuration file: {self.configFile}\n"
            f"\n"
            f"Core.Host: {self.hostName}\n"
            f"Core.Port: {self.port}\n"
            f"\n"
            f"Core.ServerRoot: {self.serverRoot}\n"
            f"Core.ConfigRoot: {self.configRoot}\n"
            f"Core.DataRoot: {self.dataRoot}\n"
            f"Core.CachedResources: {self.cachedResourcesRoot}\n"
            f"Core.LogLevel: {self.logLevelName}\n"
            f"Core.LogFile: {self.logFilePath}\n"
            f"Core.LogFormat: {self.logFormat}\n"
            f"\n"
            f"DataStore: {describeFactory(self._storeFactory)}\n"
            f"Directory: {self.directory}\n"
        )

    def replace(self, **changes: Any) -> "Configuration":
        """
        Return a new Configuration instance with changed values.
        """
        return evolve(self, **changes)
