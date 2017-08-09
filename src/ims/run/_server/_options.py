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
Command line options for the IMS server.
"""

from pathlib import Path
from sys import stderr, stdout
from textwrap import dedent
from typing import Mapping, MutableMapping, Optional, Sequence, cast

from twisted.application.runner._exit import ExitStatus, exit
from twisted.logger import (
    InvalidLogLevelError, LogLevel, jsonFileLogObserver, textFileLogObserver
)
from twisted.python.usage import Options, UsageError

from ims import __version__ as version
from ims.config import Configuration


__all__ = ()


openFile = open



class ServerOptions(Options):
    """
    Command line options for the IMS server.
    """

    defaultLogLevel = LogLevel.info


    def getSynopsis(self) -> str:
        return f"{Options.getSynopsis(self)} plugin [plugin_options]"


    def opt_version(self) -> None:
        """
        Print version and exit.
        """
        exit(ExitStatus.EX_OK, f"{version}")


    def opt_config(self, path: str) -> None:
        """
        Location of configuration file.
        """
        cast(MutableMapping, self)["configFile"] = Path(path)


    def initConfig(self) -> None:
        try:
            configFile = cast(Path, cast(Mapping, self).get("configFile"))

            if configFile is None:
                configuration = Configuration(None)
            else:
                if not configFile.is_file():
                    exit(ExitStatus.EX_CONFIG, "Config file not found.")
                configuration = Configuration(configFile)

            options = cast(Mapping, self)

            if "logFileName" in options:
                configuration.LogFilePath = Path(self["logFileName"])
            else:
                self.opt_log_file(str(configuration.LogFilePath))

            if "logFormat" in options:
                configuration.LogFormat = self["logFormat"]
            elif configuration.LogFormat is not None:
                self.opt_log_format(configuration.LogFormat)

            if "logLevel" in options:
                configuration.LogLevelName = self["logLevel"].name
            elif configuration.LogLevelName is not None:
                self.opt_log_level(configuration.LogLevelName)

            cast(MutableMapping, self)["configuration"] = configuration
        except Exception as e:
            exit(ExitStatus.EX_CONFIG, str(e))


    def opt_log_level(self, levelName: str) -> None:
        """
        Set default log level.
        (options: {options}; default: "{default}")
        """
        try:
            self["logLevel"] = LogLevel.levelWithName(levelName)
        except InvalidLogLevelError:
            raise UsageError(f"Invalid log level: {levelName}")

    opt_log_level.__doc__ = dedent(cast(str, opt_log_level.__doc__)).format(
        options=", ".join(
            '"{}"'.format(l.name) for l in LogLevel.iterconstants()
        ),
        default=defaultLogLevel.name,
    )


    def opt_log_file(self, fileName: str) -> None:
        """
        Log to file. ("-" for stdout, "+" for stderr; default: "-")
        """
        self["logFileName"] = fileName

        if fileName == "-":
            self["logFile"] = stdout
            return

        if fileName == "+":
            self["logFile"] = stderr
            return

        try:
            self["logFile"] = openFile(fileName, "a")
        except EnvironmentError as e:
            exit(
                ExitStatus.EX_IOERR,
                f"Unable to open log file {fileName!r}: {e}"
            )


    def opt_log_format(self, logFormat: str) -> None:
        """
        Log file format.
        (options: "text", "json"; default: "text" if the log file is a tty,
        otherwise "json")
        """
        logFormat = logFormat.lower()

        if logFormat == "text":
            self["fileLogObserverFactory"] = textFileLogObserver
        elif logFormat == "json":
            self["fileLogObserverFactory"] = jsonFileLogObserver
        else:
            raise UsageError(f"Invalid log format: {logFormat}")
        self["logFormat"] = logFormat

    opt_log_format.__doc__ = dedent(cast(str, opt_log_format.__doc__))


    def selectDefaultLogObserver(self) -> None:
        """
        Set :func:`fileLogObserverFactory` to the default appropriate for the
        chosen log file.
        """
        if "fileLogObserverFactory" not in self:
            logFile = self["logFile"]

            if hasattr(logFile, "isatty") and logFile.isatty():
                self["fileLogObserverFactory"] = textFileLogObserver
                self["logFormat"] = "text"
            else:
                self["fileLogObserverFactory"] = jsonFileLogObserver
                self["logFormat"] = "json"


    def parseOptions(self, options: Optional[Sequence[str]] = None) -> None:
        Options.parseOptions(self, options=options)

        self.selectDefaultLogObserver()


    def postOptions(self) -> None:
        Options.postOptions(self)

        self.initConfig()
