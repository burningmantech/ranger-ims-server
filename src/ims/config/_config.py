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
from os import environ, getcwd
from os.path import basename, sep as pathsep
from pathlib import Path
from sys import argv
from typing import Any, ClassVar, FrozenSet, Optional, Tuple, cast

from attr import attrib, attrs, evolve

from twisted.logger import Logger

from ims.auth import AuthProvider
from ims.dms import DutyManagementSystem
from ims.ext.json import jsonTextFromObject, objectFromJSONBytesIO
from ims.store import IMSDataStore
from ims.store.sqlite import DataStore

from ._urls import URLs


__all__ = (
    "Configuration",
)



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
        locationsPath: Optional[Path]        = None
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

        port = int(cast(str, valueFromConfig("PORT", "Core", "Port", "8080")))
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
        makeDirectory(configRoot)
        cls._log.info("Config root: {path}", path=configRoot)

        dataRoot = pathFromConfig(
            "DATA_ROOT", "Core", "DataRoot", serverRoot, ("data",)
        )
        makeDirectory(dataRoot)
        cls._log.info("Data root: {path}", path=dataRoot)

        databasePath = pathFromConfig(
            "DB_PATH", "Core", "Database", dataRoot, ("db.sqlite",)
        )
        cls._log.info("Database: {path}", path=databasePath)

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
        cls._log.info("Admins: {admins}", admins=imsAdmins)

        active = valueFromConfig(
            "REQUIRE_ACTIVE", "Core", "RequireActive", "true"
        )
        active = active.lower()
        if active in ("false", "no", "0"):
            requireActive = False
        else:
            requireActive = True
        cls._log.info("RequireActive: {active}", active=requireActive)

        dmsHost     = valueFromConfig("DMS_HOSTNAME", "DMS", "Hostname")
        dmsDatabase = valueFromConfig("DMS_DATABASE", "DMS", "Database")
        dmsUsername = valueFromConfig("DMS_USERNAME", "DMS", "Username")
        dmsPassword = valueFromConfig("DMS_PASSWORD", "DMS", "Password")

        cls._log.info(
            "Database: {user}@{host}/{db}",
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
            DatabasePath=databasePath,
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
        )


    ConfigFile: Optional[Path]

    CachedResourcesRoot: Path
    ConfigRoot: Path
    DatabasePath: Path
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

    _state: _State = attrib(factory=_State, init=False)


    @property
    def store(self) -> IMSDataStore:
        """
        Data store.
        """
        if self._state.store is None:
            self._state.store = DataStore(dbPath=self.DatabasePath)

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


    @property
    def locationsPath(self) -> Path:
        """
        Locations file path.
        """
        if self._state.locationsPath is None:
            self._state.locationsPath = self.DataRoot / "locations.json"

        return self._state.locationsPath


    @property
    def locationsJSONBytes(self) -> bytes:
        """
        Locations JSON data as bytes.
        """
        if self._state.locationsJSONBytes is None:
            if self.locationsPath.is_file():
                with self.locationsPath.open() as jsonStream:
                    json = objectFromJSONBytesIO(jsonStream)
                self._log.info("{count} locations", count=len(json))
                locationsJSONBytes = jsonTextFromObject(json).encode("utf-8")
            else:
                self._log.info(
                    "No locations file: {path}", path=self.locationsPath
                )
                locationsJSONBytes = jsonTextFromObject([]).encode("utf-8")

            self._state.locationsJSONBytes = locationsJSONBytes

        return self._state.locationsJSONBytes


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
            f"Core.DatabasePath: {self.DatabasePath}\n"
            f"Core.CachedResources: {self.CachedResourcesRoot}\n"
            f"Core.LogLevel: {self.LogLevelName}\n"
            f"Core.LogFile: {self.LogFilePath}\n"
            f"Core.LogFormat: {self.LogFormat}\n"
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
