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
Incident Management System web service command line tool.
"""

__all__ = [
    "WebTool",
]

from twisted.python.filepath import FilePath
from twisted.logger import Logger
from twisted.web.server import Site, Session
from twext.python.usage import (
    Executable, Options as BaseOptions, exit, ExitStatus
)

from ..data.model import Event
from ..store.istore import StorageError
from ..store.sqlite import Storage
from .log import patchCombinedLogFormatter
from .config import Configuration
from .service import WebService



class IMSSession(Session):
    sessionTimeout = 60 * 60 * 1  # 1 hour



class ConfigOptionsMixIn(object):
    """
    Mixin for L{Options} which adds options for reading an IMS config file.
    """

    def opt_config(self, path):
        """
        Location of configuration file.
        """
        self["configFile"] = FilePath(path)


    def initConfig(self):
        try:
            configFile = self.get("configFile")

            if configFile is None:
                if FilePath("./.develop").isdir():
                    dev = FilePath("./conf/imsd.conf")
                    if dev.isfile():
                        configFile = dev

            if configFile is None:
                configuration = Configuration(None)
            else:
                if not configFile.isfile():
                    exit(ExitStatus.EX_CONFIG, "Config file not found.")
                configuration = Configuration(configFile)

            if "logFile" not in self:
                self.opt_log_file(configuration.LogFile)
            if "logFormat" not in self:
                self.opt_log_format(configuration.LogFormat)
            if "logLevel" not in self:
                self.opt_log_level(configuration.LogLevel)
            if "pidFile" not in self:
                self.opt_pid_file(configuration.PIDFile)

            self["configuration"] = configuration
        except Exception as e:
            exit(ExitStatus.EX_CONFIG, unicode(e))



class WebTool(Executable):
    """
    Incident Management System web service command line tool.
    """

    log = Logger()


    class Options(BaseOptions, ConfigOptionsMixIn):
        optFlags = []

        optParameters = [
            ["port", "p", 8080, "Port to listen on."],
        ]


    def postOptions(self):
        Executable.postOptions(self)

        patchCombinedLogFormatter()

        self.options.initConfig()


    def whenRunning(self):
        config = self.options["configuration"]
        config.directory.loadRecords()
        service = WebService(config)

        host = self.options.get("host", "localhost")
        port = int(self.options["port"])

        self.log.info(
            "Setting up web service at http://{host}:{port}/",
            host=host, port=port,
        )

        factory = Site(service.resource())
        factory.sessionFactory = IMSSession

        from twisted.internet import reactor
        reactor.listenTCP(port, factory, interface=host)



class KleinTool(Executable):
    """
    Incident Management System web service command line tool.
    """

    log = Logger()


    class Options(BaseOptions, ConfigOptionsMixIn):
        optFlags = []

        optParameters = []


    def postOptions(self):
        Executable.postOptions(self)

        self.options.initConfig()

        config = self.options["configuration"]
        service = WebService(config)

        for rule in service.app.url_map.iter_rules():
            methods = list(rule.methods)
            print(
                "{rule.rule} {methods} -> {rule.endpoint}"
                .format(rule=rule, methods=methods)
            )

        exit(ExitStatus.EX_OK)



class LegacyLoadTool(Executable):
    """
    Incident Management System tool for loading data from a legacy file store
    into to a database store.
    """

    log = Logger()

    class Options(BaseOptions, ConfigOptionsMixIn):
        optFlags = []

        optParameters = []


        def __init__(self):
            BaseOptions.__init__(self)
            self.opt_log_file("-")


        def getSynopsis(self):
            return "{} datadir [datadir ...]".format(
                BaseOptions.getSynopsis(self)
            )


        def parseArgs(self, *datadirs):
            BaseOptions.parseArgs(self)
            self["fileStores"] = [FilePath(d) for d in datadirs]


    def postOptions(self):
        Executable.postOptions(self)

        self.options.initConfig()


    def whenRunning(self):
        try:
            config = self.options["configuration"]

            storage = Storage(config.DatabaseFile)

            for storeFilePath in self.options["fileStores"]:
                try:
                    storage.loadFromFileStore(storeFilePath)
                except StorageError as e:
                    self.log.critical(
                        "{error}", store=storeFilePath, error=e
                    )
                    break

        finally:
            from twisted.internet import reactor
            reactor.stop()


class JSONLoadTool(Executable):
    """
    Incident Management System tool for loading data from a JSON file into to a
    database store.
    """

    log = Logger()

    class Options(BaseOptions, ConfigOptionsMixIn):
        optFlags = []

        optParameters = []


        def __init__(self):
            BaseOptions.__init__(self)
            self.opt_log_file("-")
            self["trialRun"] = False


        def getSynopsis(self):
            return "{} event file".format(
                BaseOptions.getSynopsis(self)
            )


        def opt_trial(self):
            self["trialRun"] = True

        opt_t = opt_trial


        def parseArgs(self, eventID, fileName):
            BaseOptions.parseArgs(self)

            self["event"] = Event(eventID)
            self["filePath"] = FilePath(fileName)


    def postOptions(self):
        Executable.postOptions(self)

        self.options.initConfig()


    def whenRunning(self):
        try:
            config   = self.options["configuration"]
            event    = self.options["event"]
            filePath = self.options["filePath"]
            trialRun = self.options["trialRun"]

            storage = Storage(config.DatabaseFile)

            try:
                storage.loadFromEventJSON(event, filePath, trialRun=trialRun)
            except StorageError as e:
                self.log.critical(
                    "{error}", event=event, file=filePath, error=e
                )

        finally:
            from twisted.internet import reactor
            reactor.stop()
