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
from twisted.web.server import Site
from twext.python.usage import (
    Executable, Options as BaseOptions, exit, ExitStatus
)

from .log import patchCombinedLogFormatter
from .config import Configuration
from .service import WebService



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


    def whenRunning(self):
        self.options.initConfig()

        config = self.options["configuration"]
        config.directory.loadRecords()
        service = WebService(config)

        host = self.options.get("host", "localhost")
        port = int(self.options["port"])

        self.log.info(
            "Setting up web service at http://{host}:{port}/",
            host=host, port=port,
        )

        from twisted.internet import reactor
        reactor.listenTCP(
            port, Site(service.resource()), interface=host
        )
