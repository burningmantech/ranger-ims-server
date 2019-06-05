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

from configparser import ConfigParser, NoOptionError, NoSectionError
from enum import Enum
from os import environ, getcwd
from os.path import basename, sep as pathsep
from pathlib import Path
from sys import argv
from typing import Any, ClassVar, FrozenSet, Mapping, Optional, Tuple, cast

from attr import attrib, attrs, evolve

from twisted.logger import Logger

from ims.auth import AuthProvider
from ims.dms import DutyManagementSystem
from ims.store import IMSDataStore
from ims.store.mysql import DataStore as MySQLDataStore
from ims.store.sqlite import DataStore as SQLiteDataStore

from ._urls import URLs


__all__ = ()



@attrs(frozen=False, auto_attribs=True, auto_exc=True)
class ConfigurationError(Exception):
    """
    Configuration error.
    """

    message: str



class DataStoreFactory(Enum):
    """
    Data store type.
    """

    SQLite = SQLiteDataStore
    MySQL  = MySQLDataStore



@attrs(frozen=True, auto_attribs=True, kw_only=True)
class Configuration(object):
    """
    Configuration
    """

    _log: ClassVar = Logger()
    urls: ClassVar = URLs


    @attrs(frozen=False, auto_attribs=True, kw_only=True, cmp=False)
    class _State(object):
        """
        Internal mutable state for :class:`Configuration`.
        """

        store: Optional[IMSDataStore]        = None
        dms: Optional[DutyManagementSystem]  = None
        authProvider: Optional[AuthProvider] = None
        locationsJSONBytes: Optional[bytes]  = None


    @classmethod
    def fromConfigFile(cls, configFile: Optional[Path]) -> "Configuration":
        """
        Load the configuration.
        """
        command = basename(argv[0])

        configParser = ConfigParser()

        def readConfig(path: Optional[Path]) -> None:
            if path is None:
                cls._log.info("No configuration file specified.")
                return

            for _okFile in configParser.read(str(path)):
                cls._log.info(
                    "Read configuration file: {path}", path=path
                )
                break
            else:
                cls._log.error(
                    "Unable to read configuration file: {path}", path=path
                )

        def valueFromConfig(
            variable: str, section: str, option: str, default: str = ""
        ) -> str:
            value = environ.get(f"IMS_{variable}")

            if not value:
                try:
                    value = configParser.get(section, option)
                except (NoSectionError, NoOptionError):
                    pass

            if value:
                return value
            else:
                return default

        def pathFromConfig(
            variable: str, section: str, option: str,
            root: Path, segments: Tuple[str],
        ) -> Path:
            text = valueFromConfig(variable, section, option)

            if not text:
                path = root
                for segment in segments:
                    path = path / segment

            elif text.startswith("/"):
                path = Path(text)

            else:
                path = root
                for segment in text.split(pathsep):
                    path = path / segment

            return path

        def makeDirectory(path: Path) -> None:
            path.mkdir(exist_ok=True)

        readConfig(configFile)

        if configFile is None:
            defaultRoot = Path(getcwd())
        else:
            defaultRoot = configFile.parent.parent

        hostName = valueFromConfig("HOSTNAME", "Core", "Host", "localhost")
        cls._log.info("HostName: {hostName}", hostName=hostName)

        port = int(cast(str, valueFromConfig("PORT", "Core", "Port", "80")))
        cls._log.info("Port: {port}", port=port)

        serverRoot = pathFromConfig(
            "SERVER_ROOT", "Core", "ServerRoot",
            defaultRoot, cast(Tuple[str], ()),
        )
        makeDirectory(serverRoot)
        cls._log.info("Server root: {path}", path=serverRoot)

        configRoot = pathFromConfig(
            "CONFIG_ROOT", "Core", "ConfigRoot", serverRoot, ("conf",)
        )
        cls._log.info("Config root: {path}", path=configRoot)

        dataRoot = pathFromConfig(
            "DATA_ROOT", "Core", "DataRoot", serverRoot, ("data",)
        )
        makeDirectory(dataRoot)
        cls._log.info("Data root: {path}", path=dataRoot)

        cachedResourcesRoot = pathFromConfig(
            "CACHE_PATH", "Core", "CachedResources", dataRoot, ("cache",)
        )
        makeDirectory(cachedResourcesRoot)
        cls._log.info(
            "CachedResourcesRoot: {path}", path=cachedResourcesRoot
        )

        logLevelName = valueFromConfig("LOG_LEVEL", "Core", "LogLevel", "info")
        cls._log.info("LogLevel: {logLevel}", logLevel=logLevelName)

        logFormat = valueFromConfig("LOG_FORMAT", "Core", "LogFormat", "text")
        cls._log.info("LogFormat: {logFormat}", logFormat=logFormat)

        logFilePath = pathFromConfig(
            "LOG_FILE", "Core", "LogFile", dataRoot, (f"{command}.log",)
        )
        cls._log.info("LogFile: {path}", path=logFilePath)

        admins = valueFromConfig("ADMINS", "Core", "Admins")
        imsAdmins: FrozenSet[str] = frozenset(
            a for a in map(str.strip, admins.split(",")) if a
        )
        cls._log.info("Admins: {admins}", admins=tuple(imsAdmins))

        active = valueFromConfig(
            "REQUIRE_ACTIVE", "Core", "RequireActive", "true"
        )
        active = active.lower()
        if active in ("false", "no", "0"):
            requireActive = False
        else:
            requireActive = True
        cls._log.info("RequireActive: {active}", active=requireActive)

        storeName = valueFromConfig(
            "DATA_STORE", "Core", "DataStore", "SQLite"
        )
        try:
            storeFactory = DataStoreFactory[storeName]
        except KeyError:
            raise ConfigurationError(f"Unknown data store: {storeName}")
        cls._log.info("DataStore: {storeName}", storeName=storeName)

        storeArguments: Mapping[str, Any]

        if storeFactory is DataStoreFactory.SQLite:
            dbPath = pathFromConfig(
                "DB_PATH", "Store:SQLite", "File", dataRoot, ("db.sqlite",)
            )
            cls._log.info("Database: {path}", path=dbPath)
            storeArguments = dict(dbPath=dbPath)

        if storeFactory is DataStoreFactory.MySQL:
            storeHost = valueFromConfig(
                "DB_HOST_NAME", "Store:MySQL", "HostName", "localhost"
            )
            storePort = int(valueFromConfig(
                "DB_HOST_PORT", "Store:MySQL", "HostPort", "3306"
            ))
            storeDatabase = valueFromConfig(
                "DB_DATABASE", "Store:MySQL", "Database"
            )
            storeUser = valueFromConfig(
                "DB_USER_NAME", "Store:MySQL", "UserName"
            )
            storePassword = valueFromConfig(
                "DB_PASSWORD", "Store:MySQL", "Password"
            )
            cls._log.info(
                "Database: {user}@{host}:{port}",
                user=storeUser, host=storeHost, port=storePort,
            )
            storeArguments = dict(
                hostName=storeHost,
                hostPort=storePort,
                database=storeDatabase,
                username=storeUser,
                password=storePassword,
            )

        dmsHost     = valueFromConfig("DMS_HOSTNAME", "DMS", "Hostname")
        dmsDatabase = valueFromConfig("DMS_DATABASE", "DMS", "Database")
        dmsUsername = valueFromConfig("DMS_USERNAME", "DMS", "Username")
        dmsPassword = valueFromConfig("DMS_PASSWORD", "DMS", "Password")

        cls._log.info(
            "DMS: {user}@{host}/{db}",
            user=dmsUsername, host=dmsHost, db=dmsDatabase,
        )

        masterKey = valueFromConfig("MASTER_KEY", "Core", "MasterKey")

        #
        # Persist some objects
        #

        return cls(
            ConfigFile=configFile,

            CachedResourcesRoot=cachedResourcesRoot,
            ConfigRoot=configRoot,
            DataRoot=dataRoot,
            DMSDatabase=dmsDatabase,
            DMSHost=dmsHost,
            DMSPassword=dmsPassword,
            DMSUsername=dmsUsername,
            HostName=hostName,
            IMSAdmins=imsAdmins,
            LogFilePath=logFilePath,
            LogFormat=logFormat,
            LogLevelName=logLevelName,
            MasterKey=masterKey,
            Port=port,
            RequireActive=requireActive,
            ServerRoot=serverRoot,
            StoreArguments=storeArguments,
            StoreFactory=storeFactory,
        )


    ConfigFile: Optional[Path]

    CachedResourcesRoot: Path
    ConfigRoot: Path
    DataRoot: Path
    DMSDatabase: str
    DMSHost: str
    DMSPassword: str
    DMSUsername: str
    HostName: str
    IMSAdmins: FrozenSet[str]
    LogFilePath: Path
    LogFormat: str
    LogLevelName: str
    MasterKey: str
    Port: int
    RequireActive: bool
    ServerRoot: Path
    StoreArguments: Mapping[str, Any]
    StoreFactory: DataStoreFactory

    _state: _State = attrib(factory=_State, init=False)


    @property
    def store(self) -> IMSDataStore:
        """
        Data store.
        """
        if self._state.store is None:
            self._state.store = self.StoreFactory.value(**self.StoreArguments)

        return self._state.store


    @property
    def dms(self) -> DutyManagementSystem:
        """
        Duty Management System.
        """
        if self._state.dms is None:
            self._state.dms = DutyManagementSystem(
                host=self.DMSHost, database=self.DMSDatabase,
                username=self.DMSUsername, password=self.DMSPassword,
            )

        return self._state.dms


    @property
    def authProvider(self) -> AuthProvider:
        """
        Auth provider.
        """
        if self._state.authProvider is None:
            self._state.authProvider = AuthProvider(
                store=self.store, dms=self.dms,
                requireActive=self.RequireActive,
                adminUsers=self.IMSAdmins, masterKey=self.MasterKey,
            )

        return self._state.authProvider


    def __str__(self) -> str:
        return (
            f"Configuration file: {self.ConfigFile}\n"
            f"\n"
            f"Core.Host: {self.HostName}\n"
            f"Core.Port: {self.Port}\n"
            f"\n"
            f"Core.ServerRoot: {self.ServerRoot}\n"
            f"Core.ConfigRoot: {self.ConfigRoot}\n"
            f"Core.DataRoot: {self.DataRoot}\n"
            f"Core.CachedResources: {self.CachedResourcesRoot}\n"
            f"Core.LogLevel: {self.LogLevelName}\n"
            f"Core.LogFile: {self.LogFilePath}\n"
            f"Core.LogFormat: {self.LogFormat}\n"
            f"\n"
            f"DB.Store: {self.StoreFactory}\n"
            f"DB.Arguments: {self.StoreArguments}\n"
            f"\n"
            f"DMS.Hostname: {self.DMSHost}\n"
            f"DMS.Database: {self.DMSDatabase}\n"
            f"DMS.Username: {self.DMSUsername}\n"
            f"DMS.Password: {self.DMSPassword}\n"
        )


    def replace(self, **changes: Any) -> "Configuration":
        """
        Return a new Configuration instance with changed values.
        """
        return evolve(self, **changes)
