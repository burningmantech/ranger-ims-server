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

from __future__ import print_function

"""
Server
"""

__all__ = [
    "Configuration",
]

from os import environ
from os.path import sep as pathsep
from re import compile as regex_compile
from time import tzset, time

from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError

from twisted.python import log as txlog
from twisted.python.filepath import FilePath

from .tz import FixedOffsetTimeZone
from .data import IncidentType
from .json import json_as_text, json_from_file
from .dms import DutyManagementSystem
from .store import Storage, ReadOnlyStorage



if False:
    class PrintLogger(object):
        def msg(self, text):
            print(text)
            txlog.msg(text)

        def err(self, text):
            print(text)
            txlog.err(text)

    log = PrintLogger()
else:
    log = txlog


class Configuration (object):
    def __init__(self, configFile):
        self.configFile = configFile
        self.load()


    def __str__(self):
        return (
            "Configuration file: {self.configFile}\n"
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
            for okFile in configParser.read((configFile.path,)):
                log.msg("Read configuration file: {0}".format(configFile.path))
            else:
                log.msg("No configuration file read.")

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

        readConfig(self.configFile)

        self.ServerRoot = filePathFromConfig(
            "Core", "ServerRoot",
            self.configFile.parent().parent(), ()
        )
        log.msg("Server root: {0}".format(self.ServerRoot.path))

        self.ConfigRoot = filePathFromConfig(
            "Core", "ConfigRoot",
            self.ServerRoot, ("conf",)
        )
        log.msg("Config root: {0}".format(self.ConfigRoot.path))

        self.UserDB = filePathFromConfig(
            "Core", "UserDB",
            self.ConfigRoot, ("users.pwdb",)
        )
        log.msg("User DB: {0}".format(self.UserDB.path))

        self.DataRoot = filePathFromConfig(
            "Core", "DataRoot",
            self.ServerRoot, ("data",)
        )
        log.msg("Data root: {0}".format(self.DataRoot.path))

        self.Resources = filePathFromConfig(
            "Core", "Resources",
            self.ServerRoot, ("resources",)
        )
        log.msg("Resources: {0}".format(self.Resources.path))

        self.CachedResources = filePathFromConfig(
            "Core", "CachedResources",
            self.ServerRoot, ("cached",)
        )
        log.msg("CachedResources: {0}".format(self.CachedResources.path))

        rejectClients = valueFromConfig("Core", "RejectClients", "")
        rejectClients = tuple([e for e in rejectClients.split("\n") if e])

        self.RejectClients = rejectClients
        self.RejectClientsRegex = tuple([
            regex_compile(e)
            for e in rejectClients
        ])
        log.msg("RejectClients: {0}".format(self.RejectClients))

        timeZoneName = valueFromConfig(
            "Core", "TimeZone", "America/Los_Angeles"
        )

        environ["TZ"] = timeZoneName
        tzset()

        self.TimeZone = FixedOffsetTimeZone.fromLocalTimeStamp(time())

        self.ReadOnly = (
            valueFromConfig("Core", "ReadOnly", "false") == "true"
        )
        log.msg("ReadOnly: {0}".format(self.ReadOnly))

        self.Debug = (
            valueFromConfig("Core", "Debug", "false") == "true"
        )
        log.msg("Debug: {0}".format(self.Debug))

        self.DMSHost     = valueFromConfig("DMS", "Hostname", None)
        self.DMSDatabase = valueFromConfig("DMS", "Database", None)
        self.DMSUsername = valueFromConfig("DMS", "Username", None)
        self.DMSPassword = valueFromConfig("DMS", "Password", None)

        self.IncidentTypes = (
            u"Art",
            u"Assault",
            u"Courtesy Notice",
            u"Commerce",
            u"Echelon",
            u"Eviction",
            u"Fire",
            u"Gate",
            u"Green Dot",
            u"HQ",
            u"Law Enforcement",
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

        #
        # Persist some objects
        #

        self.dms = DutyManagementSystem(
            host=self.DMSHost,
            database=self.DMSDatabase,
            username=self.DMSUsername,
            password=self.DMSPassword,
        )

        if self.ReadOnly:
            storageClass = ReadOnlyStorage
        else:
            storageClass = Storage

        storage = storageClass(self.DataRoot)
        self.storage = storage

        self.IncidentTypesJSON = json_as_text(self.IncidentTypes)


        locationsFile = self.configFile.sibling("locations.json")

        if locationsFile.isfile():
            with locationsFile.open() as jsonStrem:
                json = json_from_file(jsonStrem)
            self.locationsJSONText = json_as_text(json)
