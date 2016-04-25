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

from __future__ import print_function

__all__ = [
    "Configuration",
]

import sys
from os import environ, getcwd
from os.path import sep as pathsep
from re import compile as regex_compile
from time import tzset, time

from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError

from twisted.python.filepath import FilePath
from twisted.logger import Logger, textFileLogObserver

from ..tz import FixedOffsetTimeZone
from ..data import IncidentType
from ..json import textFromJSON, jsonFromFile
from ..dms.dms import DutyManagementSystem
from ..store import MultiStorage



class Configuration (object):
    """
    Configuration
    """

    log = Logger(observer=textFileLogObserver(sys.stdout))


    def __init__(self, configFile):
        self.ConfigFile = configFile
        self.load()


    def __str__(self):
        return (
            "Configuration file: {self.ConfigFile}\n"
            "\n"
            "Core.ServerRoot: {self.ServerRoot}\n"
            "Core.ConfigRoot: {self.ConfigRoot}\n"
            "Core.UserDB: {self.UserDB}\n"
            "Core.DataRoot: {self.DataRoot}\n"
            "Core.Resources: {self.Resources}\n"
            "Core.CachedResources: {self.CachedResources}\n"
            "Core.RejectClients: {self.RejectClients}\n"
            "Core.TimeZone: {self.TimeZone}\n"
            "Core.ReadOnly: {self.ReadOnly}\n"
            "Core.Debug: {self.Debug}\n"
            "\n"
            "DMS.Hostname: {self.DMSHost}\n"
            "DMS.Database: {self.DMSDatabase}\n"
            "DMS.Username: {self.DMSUsername}\n"
            "DMS.Password: {self.DMSPassword}\n"
            "\n"
            "Incident types: {self.IncidentTypes}\n"
        ).format(self=self)


    def load(self):
        configParser = SafeConfigParser()

        def readConfig(configFile):
            if configFile is None:
                self.log.info("No configuration file specified.")
                return

            okFile = None

            for okFile in configParser.read(configFile.path,):
                self.log.info(
                    "Read configuration file: {configFile.path}",
                    configFile=configFile
                )

            self.log.error(
                "Unable to read configuration file: {file.path}",
                file=configFile
            )

        def valueFromConfig(section, option, default):
            try:
                value = configParser.get(section, option)
                if value:
                    return value
                else:
                    return default
            except (NoSectionError, NoOptionError):
                return default

        def filePathFromConfig(section, option, root, segments):
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

        self.ServerRoot = filePathFromConfig(
            "Core", "ServerRoot", defaultRoot, ()
        )
        self.log.info(
            "Server root: {serverRoot.path}", serverRoot=self.ServerRoot
        )

        self.ConfigRoot = filePathFromConfig(
            "Core", "ConfigRoot", self.ServerRoot, ("conf",)
        )
        self.log.info(
            "Config root: {configRoot.path}", configRoot=self.ConfigRoot
        )

        self.UserDB = filePathFromConfig(
            "Core", "UserDB", self.ConfigRoot, ("users.pwdb",)
        )
        self.log.info("User DB: {userDB.path}", userDB=self.UserDB)

        self.DataRoot = filePathFromConfig(
            "Core", "DataRoot", self.ServerRoot, ("data",)
        )
        self.log.info(
            "Data root: {dataRoot.path}", dataRoot=self.DataRoot
        )

        self.Resources = filePathFromConfig(
            "Core", "Resources", self.ServerRoot, ("resources",)
        )
        self.log.info(
            "Resources: {resources.path}", resources=self.Resources
        )

        self.CachedResources = filePathFromConfig(
            "Core", "CachedResources", self.ServerRoot, ("cached",)
        )
        self.log.info(
            "CachedResources: {cachedResources.path}",
            cachedResources=self.CachedResources
        )

        rejectClients = valueFromConfig("Core", "RejectClients", "")
        rejectClients = tuple([e for e in rejectClients.split("\n") if e])

        self.RejectClients = rejectClients
        self.RejectClientsRegex = tuple([
            regex_compile(e)
            for e in rejectClients
        ])
        self.log.info(
            "RejectClients: {rejectClients}", rejectClients=self.RejectClients
        )

        timeZoneName = valueFromConfig(
            "Core", "TimeZone", "America/Los_Angeles"
        )

        environ["TZ"] = timeZoneName
        tzset()

        self.TimeZone = FixedOffsetTimeZone.fromLocalTimeStamp(time())

        self.ReadOnly = (
            valueFromConfig("Core", "ReadOnly", "false") == "true"
        )
        self.log.info("ReadOnly: {readOnly}", readOnly=self.ReadOnly)

        self.Debug = (
            valueFromConfig("Core", "Debug", "false") == "true"
        )
        self.log.info("Debug: {debug}", debug=self.Debug)

        self.DMSHost     = valueFromConfig("DMS", "Hostname", None)
        self.DMSDatabase = valueFromConfig("DMS", "Database", None)
        self.DMSUsername = valueFromConfig("DMS", "Username", None)
        self.DMSPassword = valueFromConfig("DMS", "Password", None)

        self.log.info(
            "Database: {user}@{host}/{db}",
            user=self.DMSUsername, host=self.DMSHost, db=self.DMSDatabase,
        )

        self.IncidentTypes = (
            u"Art",
            u"Assault",
            u"Courtesy Notice",
            u"Commerce",
            u"Drone",
            u"Echelon",
            u"Eviction",
            u"Fire",
            u"Gate",
            u"Green Dot",
            u"HQ",
            u"Law Enforcement",
            u"Laser",
            u"Lost Child",
            u"Medical",
            u"Mental Health",
            u"Missing Person",
            u"MOOP",
            u"SITE",
            u"Staff",
            u"Theme Camp",
            u"Vehicle",

            IncidentType.Admin.value,
            IncidentType.Junk.value,
        )

        self.log.info(
            "{count} incident types",
            incident_types=self.IncidentTypes, count=len(self.IncidentTypes),
        )

        #
        # Persist some objects
        #

        self.dms = DutyManagementSystem(
            host=self.DMSHost,
            database=self.DMSDatabase,
            username=self.DMSUsername,
            password=self.DMSPassword,
        )

        self.storage = MultiStorage(self.DataRoot, self.ReadOnly)

        self.IncidentTypesJSONBytes = (
            textFromJSON(self.IncidentTypes).encode("utf-8")
        )

        locationsFile = self.ConfigRoot.sibling("locations.json")

        if locationsFile.isfile():
            with locationsFile.open() as jsonStrem:
                json = jsonFromFile(jsonStrem)
            self.log.info("{count} locations", count=len(json))
            self.locationsJSONBytes = textFromJSON(json).encode("utf-8")
        else:
            self.log.info("No locations file: {file.path}", file=locationsFile)
            self.locationsJSONBytes = textFromJSON([]).encode("utf-8")
