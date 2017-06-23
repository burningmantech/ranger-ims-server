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

from typing import Any, List, Mapping, MutableMapping, cast

from twext.python.usage import (
    Executable, ExitStatus, Options as BaseOptions, exit
)

from twisted.logger import Logger
from twisted.python.filepath import FilePath
from twisted.web.server import Session, Site

from ims.model import Event
from ims.store import StorageError
from ims.store.sqlite import DataStore

from .config import Configuration
from .log import patchCombinedLogFormatter
from .service import WebService


__all__ = (
    "WebTool",
)



class IMSSession(Session):
    sessionTimeout = 60 * 60 * 1  # 1 hour



class ConfigOptionsMixIn(object):
    """
    Mixin for L{Options} which adds options for reading an IMS config file.
    """

    def opt_config(self, path: str) -> None:
        """
        Location of configuration file.
        """
        cast(MutableMapping, self)["configFile"] = FilePath(path)


    def initConfig(self) -> None:
        try:
            configFile = cast(Mapping, self).get("configFile")

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

            if "logFile" not in cast(Mapping, self):
                self.opt_log_file(configuration.LogFile)
            if "logFormat" not in cast(Mapping, self):
                self.opt_log_format(configuration.LogFormat)
            if "logLevel" not in cast(Mapping, self):
                self.opt_log_level(configuration.LogLevel)
            if "pidFile" not in cast(Mapping, self):
                self.opt_pid_file(configuration.PIDFile)

            cast(MutableMapping, self)["configuration"] = configuration
        except Exception as e:
            exit(ExitStatus.EX_CONFIG, str(e))



class WebTool(Executable):
    """
    Incident Management System web service command line tool.
    """

    log = Logger()


    class Options(BaseOptions, ConfigOptionsMixIn):
        """
        Tool options.
        """

        optFlags: List[str] = []

        optParameters: List[Any] = [
            ["port", "p", 8080, "Port to listen on."],
        ]


    def postOptions(self) -> None:
        """
        See L{Executable.postOptions}.
        """
        Executable.postOptions(self)

        patchCombinedLogFormatter()

        self.options.initConfig()


    def whenRunning(self) -> None:
        """
        See L{Executable.whenRunning}.
        """
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
        """
        Tool options.
        """

        optFlags: List[str] = []

        optParameters: List[Any] = []


    def postOptions(self) -> None:
        """
        See L{Executable.postOptions}.
        """
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



class JSONLoadTool(Executable):
    """
    Incident Management System tool for loading data from a JSON file into to a
    database store.
    """

    log = Logger()

    class Options(BaseOptions, ConfigOptionsMixIn):
        """
        Tool options.
        """

        optFlags: List[str] = []

        optParameters: List[Any] = []


        def __init__(self) -> None:
            BaseOptions.__init__(self)
            self.opt_log_file("-")
            self["trialRun"] = False


        def getSynopsis(self) -> str:
            """
            See L{BaseOptions.getSynopsis}.
            """
            return "{} event file".format(
                BaseOptions.getSynopsis(self)
            )


        def opt_trial(self) -> None:
            """
            Path to trial executable
            """
            self["trialRun"] = True

        opt_t = opt_trial


        def parseArgs(self, eventID: str, fileName: str) -> None:
            """
            See L{BaseOptions.parseArgs}.
            """
            BaseOptions.parseArgs(self)

            self["event"] = Event(eventID)
            self["filePath"] = FilePath(fileName)


    def postOptions(self) -> None:
        """
        See L{Executable.postOptions}.
        """
        Executable.postOptions(self)

        self.options.initConfig()


    def whenRunning(self) -> None:
        """
        See L{Executable.whenRunning}.
        """
        try:
            config   = self.options["configuration"]
            event    = self.options["event"]
            filePath = self.options["filePath"]
            trialRun = self.options["trialRun"]

            storage = DataStore(config.DatabaseFile)

            try:
                storage.loadFromEventJSON(event, filePath, trialRun=trialRun)
            except StorageError as e:
                self.log.critical(
                    "{error}", event=event, file=filePath, error=e
                )

        finally:
            from twisted.internet import reactor
            reactor.stop()
