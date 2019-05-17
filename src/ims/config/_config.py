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
from os import getcwd
from os.path import basename, sep as pathsep
from pathlib import Path
from sys import argv
from typing import Any, ClassVar, FrozenSet, Optional, Tuple, cast

from attr import attrs, evolve

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
            section: str, option: str, default: Optional[str]
        ) -> Optional[str]:
            try:
                value = configParser.get(section, option)
                if value:
                    return value
                else:
                    return default
            except (NoSectionError, NoOptionError):
                return default

        def pathFromConfig(
            section: str, option: str, root: Path, segments: Tuple[str]
        ) -> Path:
            if section is None:
                text = None
            else:
                text = valueFromConfig(section, option, None)

            if text is None:
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

        hostName = valueFromConfig("Core", "Host", "localhost")
        cls._log.info("HostName: {hostName}", hostName=hostName)

        port = int(cast(str, valueFromConfig("Core", "Port", "8080")))
        cls._log.info("Port: {port}", port=port)

        serverRoot = pathFromConfig(
            "Core", "ServerRoot", defaultRoot, cast(Tuple[str], ())
        )
        makeDirectory(serverRoot)
        cls._log.info("Server root: {path}", path=serverRoot)

        configRoot = pathFromConfig(
            "Core", "ConfigRoot", serverRoot, ("conf",)
        )
        makeDirectory(configRoot)
        cls._log.info("Config root: {path}", path=configRoot)

        dataRoot = pathFromConfig(
            "Core", "DataRoot", serverRoot, ("data",)
        )
        makeDirectory(dataRoot)
        cls._log.info("Data root: {path}", path=dataRoot)

        databasePath = pathFromConfig(
            "Core", "Database", dataRoot, ("db.sqlite",)
        )
        cls._log.info("Database: {path}", path=databasePath)

        cachedResourcesPath = pathFromConfig(
            "Core", "CachedResources", dataRoot, ("cache",)
        )
        makeDirectory(cachedResourcesPath)
        cls._log.info(
            "CachedResourcesPath: {path}", path=cachedResourcesPath
        )

        logLevelName = valueFromConfig("Core", "LogLevel", "info")
        cls._log.info("LogLevel: {logLevel}", logLevel=logLevelName)

        logFormat = valueFromConfig("Core", "LogFormat", "text")
        cls._log.info("LogFormat: {logFormat}", logFormat=logFormat)

        logFilePath = pathFromConfig(
            "Core", "LogFile", dataRoot, (f"{command}.log",)
        )
        cls._log.info("LogFile: {path}", path=logFilePath)

        admins = cast(str, valueFromConfig("Core", "Admins", ""))
        imsAdmins: FrozenSet[str] = frozenset(
            a.strip() for a in admins.split(",")
        )
        cls._log.info("Admins: {admins}", admins=imsAdmins)

        active = (
            cast(str, valueFromConfig("Core", "RequireActive", "true")).lower()
        )
        if active in ("false", "no", "0"):
            requireActive = False
        else:
            requireActive = True
        cls._log.info("RequireActive: {active}", active=requireActive)

        dmsHost     = valueFromConfig("DMS", "Hostname", None)
        dmsDatabase = valueFromConfig("DMS", "Database", None)
        dmsUsername = valueFromConfig("DMS", "Username", None)
        dmsPassword = valueFromConfig("DMS", "Password", None)

        cls._log.info(
            "Database: {user}@{host}/{db}",
            user=dmsUsername, host=dmsHost, db=dmsDatabase,
        )

        masterKey = valueFromConfig("Core", "MasterKey", None)

        #
        # Persist some objects
        #

        dms = DutyManagementSystem(
            host=dmsHost, database=dmsDatabase,
            username=dmsUsername, password=dmsPassword,
        )
        store: IMSDataStore = DataStore(dbPath=databasePath)

        authProvider = AuthProvider(
            store=store, dms=dms,
            requireActive=requireActive,
            adminUsers=imsAdmins, masterKey=masterKey,
        )

        locationsPath = dataRoot / "locations.json"

        if locationsPath.is_file():
            with locationsPath.open() as jsonStrem:
                json = objectFromJSONBytesIO(jsonStrem)
            cls._log.info("{count} locations", count=len(json))
            locationsJSONBytes = jsonTextFromObject(json).encode("utf-8")
        else:
            cls._log.info("No locations file: {path}", path=locationsPath)
            locationsJSONBytes = jsonTextFromObject([]).encode("utf-8")

        return cls(
            ConfigFile=configFile,

            CachedResourcesPath=cachedResourcesPath,
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

            store=store, dms=dms, authProvider=authProvider,
            locationsPath=locationsPath, locationsJSONBytes=locationsJSONBytes,
        )


    ConfigFile: Optional[Path]

    CachedResourcesPath: Path
    ConfigRoot: Path
    DatabasePath: Path
    DataRoot: Path
    DMSDatabase: Optional[str]
    DMSHost: Optional[str]
    DMSPassword: Optional[str]
    DMSUsername: Optional[str]
    HostName: Optional[str]
    IMSAdmins: FrozenSet[str]
    LogFilePath: Path
    LogFormat: Optional[str]
    LogLevelName: Optional[str]
    MasterKey: Optional[str]
    Port: int
    RequireActive: bool
    ServerRoot: Path

    # FIXME: make these computed properties
    store: IMSDataStore
    dms: DutyManagementSystem
    authProvider: AuthProvider
    locationsPath: Path
    locationsJSONBytes: bytes


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
            f"Core.DatabaseFile: {self.DatabasePath}\n"
            f"Core.CachedResources: {self.CachedResourcesPath}\n"
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
