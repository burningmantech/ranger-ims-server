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
Server
"""

from configparser import ConfigParser, NoOptionError, NoSectionError
from os import getcwd
from os.path import basename, sep as pathsep
from pathlib import Path
from sys import argv
from typing import Optional, Set, Tuple, cast

from twisted.logger import Logger
from twisted.python.filepath import FilePath

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


    def __init__(self, configFile: FilePath) -> None:
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
            "Core.DatabaseFile: {self.DatabaseFile}\n"
            "Core.CachedResources: {self.CachedResources}\n"
            "Core.LogLevel: {self.LogLevel}\n"
            "Core.LogFile: {self.LogFileName}\n"
            "Core.LogFormat: {self.LogFormat}\n"
            "Core.PIDFile: {self.PIDFile}\n"
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

        def readConfig(configFile: FilePath) -> None:
            if configFile is None:
                self._log.info("No configuration file specified.")
                return

            for _okFile in configParser.read(configFile.path,):
                self._log.info(
                    "Read configuration file: {configFile.path}",
                    configFile=configFile
                )
                break
            else:
                self._log.error(
                    "Unable to read configuration file: {file.path}",
                    file=configFile
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

        def filePathFromConfig(
            section: str, option: str, root: FilePath, segments: Tuple[str]
        ) -> FilePath:
            if section is None:
                path = None
            else:
                path = valueFromConfig(section, option, None)

            if path is None:
                fp = root
                for segment in segments:
                    fp = fp.child(segment)

            elif path.startswith("/"):
                fp = FilePath(path)

            else:
                fp = root
                for segment in path.split(pathsep):
                    fp = fp.child(segment)

            return fp

        readConfig(self.ConfigFile)

        if self.ConfigFile is None:
            defaultRoot = FilePath(getcwd())
        else:
            defaultRoot = self.ConfigFile.parent().parent()

        self.HostName = valueFromConfig("Core", "Host", "localhost")
        self._log.info("HostName: {hostName}", hostName=self.HostName)

        self.Port = int(cast(str, valueFromConfig("Core", "Port", "8080")))
        self._log.info("Port: {port}", port=self.Port)

        self.ServerRoot = filePathFromConfig(
            "Core", "ServerRoot", defaultRoot, cast(Tuple[str], ())
        )
        self._log.info(
            "Server root: {serverRoot.path}", serverRoot=self.ServerRoot
        )

        self.ConfigRoot = filePathFromConfig(
            "Core", "ConfigRoot", self.ServerRoot, ("conf",)
        )
        self._log.info(
            "Config root: {configRoot.path}", configRoot=self.ConfigRoot
        )

        self.DataRoot = filePathFromConfig(
            "Core", "DataRoot", self.ServerRoot, ("data",)
        )
        self._log.info(
            "Data root: {dataRoot.path}", dataRoot=self.DataRoot
        )

        self.DatabaseFile = filePathFromConfig(
            "Core", "Database", self.DataRoot, ("db.sqlite",)
        )
        self._log.info(
            "Database: {db.path}", db=self.DatabaseFile
        )

        self.CachedResources = filePathFromConfig(
            "Core", "CachedResources", self.DataRoot, ("cache",)
        )
        self._log.info(
            "CachedResources: {cachedResources.path}",
            cachedResources=self.CachedResources
        )

        self.LogLevelName = valueFromConfig("Core", "LogLevel", "info")
        self._log.info("LogLevel: {logLevel}", logLevel=self.LogLevelName)

        self.LogFormat = valueFromConfig("Core", "LogFormat", "text")
        self._log.info("LogFormat: {logFormat}", logFormat=self.LogFormat)

        self.LogFileName = filePathFromConfig(
            "Core", "LogFile", self.DataRoot, ("{}.log".format(command),)
        ).path
        self._log.info(
            "LogFile: {logFile}", logFile=self.LogFileName
        )

        self.PIDFile = filePathFromConfig(
            "Core", "PIDFile", self.DataRoot, ("{}.pid".format(command),)
        ).path
        self._log.info(
            "PIDFile: {pidFile}", pidFile=self.PIDFile
        )

        admins = valueFromConfig("Core", "Admins", "")
        if admins is None:
            self.IMSAdmins: Set[str] = set()
        else:
            self.IMSAdmins = set(a.strip() for a in admins.split(","))
        self._log.info(
            "Admins: {admins}", admins=self.IMSAdmins
        )

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

        self.storage: IMSDataStore = DataStore(
            dbPath=Path(self.DatabaseFile.path)
        )

        locationsFile = self.ConfigRoot.sibling("locations.json")

        if locationsFile.isfile():
            with locationsFile.open() as jsonStrem:
                json = objectFromJSONBytesIO(jsonStrem)
            self._log.info("{count} locations", count=len(json))
            self.locationsJSONBytes = jsonTextFromObject(json).encode("utf-8")
        else:
            self._log.info(
                "No locations file: {file.path}", file=locationsFile
            )
            self.locationsJSONBytes = jsonTextFromObject([]).encode("utf-8")
