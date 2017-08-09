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
from typing import Optional, Set, Tuple, cast

from twisted.logger import Logger

from ims.dms import DutyManagementSystem
from ims.ext.json import jsonTextFromObject, objectFromJSONBytesIO
from ims.store import IMSDataStore
from ims.store.sqlite import DataStore

from ._urls import URLs

IMSDataStore, Set  # silence linter


__all__ = (
    "Configuration",
)



class Configuration(object):
    """
    Configuration
    """

    _log = Logger()

    urls = URLs


    def __init__(self, configFile: Optional[Path]) -> None:
        """
        @param configFile: The configuration file to load.
        """
        self.ConfigFile = configFile
        self.load()


    def __str__(self) -> str:
        return (
            "Configuration file: {self.ConfigFile}\n"
            "\n"
            "Core.Host: {self.HostName}\n"
            "Core.Port: {self.PortNumber}\n"
            "\n"
            "Core.ServerRoot: {self.ServerRoot}\n"
            "Core.ConfigRoot: {self.ConfigRoot}\n"
            "Core.DataRoot: {self.DataRoot}\n"
            "Core.DatabaseFile: {self.DatabasePath}\n"
            "Core.CachedResources: {self.CachedResourcesPath}\n"
            "Core.LogLevel: {self.LogLevel}\n"
            "Core.LogFile: {self.LogFilePath}\n"
            "Core.LogFormat: {self.LogFormat}\n"
            "\n"
            "DMS.Hostname: {self.DMSHost}\n"
            "DMS.Database: {self.DMSDatabase}\n"
            "DMS.Username: {self.DMSUsername}\n"
            "DMS.Password: {self.DMSPassword}\n"
        ).format(self=self)


    def load(self) -> None:
        """
        Load the configuration.
        """
        command = basename(argv[0])

        configParser = ConfigParser()

        def readConfig(path: Optional[Path]) -> None:
            if path is None:
                self._log.info("No configuration file specified.")
                return

            for _okFile in configParser.read(str(path)):
                self._log.info(
                    "Read configuration file: {path}", path=path
                )
                break
            else:
                self._log.error(
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

        readConfig(self.ConfigFile)

        if self.ConfigFile is None:
            defaultRoot = Path(getcwd())
        else:
            defaultRoot = self.ConfigFile.parent.parent

        self.HostName = valueFromConfig("Core", "Host", "localhost")
        self._log.info("HostName: {hostName}", hostName=self.HostName)

        self.Port = int(cast(str, valueFromConfig("Core", "Port", "8080")))
        self._log.info("Port: {port}", port=self.Port)

        self.ServerRoot = pathFromConfig(
            "Core", "ServerRoot", defaultRoot, cast(Tuple[str], ())
        )
        self._log.info("Server root: {path}", path=self.ServerRoot)

        self.ConfigRoot = pathFromConfig(
            "Core", "ConfigRoot", self.ServerRoot, ("conf",)
        )
        self._log.info("Config root: {path}", path=self.ConfigRoot)

        self.DataRoot = pathFromConfig(
            "Core", "DataRoot", self.ServerRoot, ("data",)
        )
        self._log.info("Data root: {path}", path=self.DataRoot)

        self.DatabasePath = pathFromConfig(
            "Core", "Database", self.DataRoot, ("db.sqlite",)
        )
        self._log.info("Database: {path}", path=self.DatabasePath)

        self.CachedResourcesPath = pathFromConfig(
            "Core", "CachedResources", self.DataRoot, ("cache",)
        )
        self._log.info(
            "CachedResourcesPath: {path}", path=self.CachedResourcesPath
        )

        self.LogLevelName = valueFromConfig("Core", "LogLevel", "info")
        self._log.info("LogLevel: {logLevel}", logLevel=self.LogLevelName)

        self.LogFormat = valueFromConfig("Core", "LogFormat", "text")
        self._log.info("LogFormat: {logFormat}", logFormat=self.LogFormat)

        self.LogFilePath = pathFromConfig(
            "Core", "LogFile", self.DataRoot, ("{}.log".format(command),)
        )
        self._log.info("LogFile: {path}", path=self.LogFilePath)

        admins = valueFromConfig("Core", "Admins", "")
        if admins is None:
            self.IMSAdmins: Set[str] = set()
        else:
            self.IMSAdmins = set(a.strip() for a in admins.split(","))
        self._log.info("Admins: {admins}", admins=self.IMSAdmins)

        self.DMSHost     = valueFromConfig("DMS", "Hostname", None)
        self.DMSDatabase = valueFromConfig("DMS", "Database", None)
        self.DMSUsername = valueFromConfig("DMS", "Username", None)
        self.DMSPassword = valueFromConfig("DMS", "Password", None)

        self._log.info(
            "Database: {user}@{host}/{db}",
            user=self.DMSUsername, host=self.DMSHost, db=self.DMSDatabase,
        )

        self.masterKey = valueFromConfig("Core", "MasterKey", None)

        #
        # Persist some objects
        #

        self.dms = DutyManagementSystem(
            host=self.DMSHost,
            database=self.DMSDatabase,
            username=self.DMSUsername,
            password=self.DMSPassword,
        )

        self.storage: IMSDataStore = DataStore(dbPath=self.DatabasePath)

        locationsPath = self.DataRoot / "locations.json"

        if locationsPath.is_file():
            with locationsPath.open() as jsonStrem:
                json = objectFromJSONBytesIO(jsonStrem)
            self._log.info("{count} locations", count=len(json))
            self.locationsJSONBytes = jsonTextFromObject(json).encode("utf-8")
        else:
            self._log.info("No locations file: {path}", path=locationsPath)
            self.locationsJSONBytes = jsonTextFromObject([]).encode("utf-8")
