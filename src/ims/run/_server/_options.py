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
from typing import (
    ClassVar, IO, Mapping, MutableMapping, Optional, Sequence, cast
)

from attr import attrs

from twisted.application.runner._exit import ExitStatus, exit
from twisted.logger import (
    InvalidLogLevelError, LogLevel, Logger,
    jsonFileLogObserver, textFileLogObserver,
)
from twisted.python.usage import Options as BaseOptions, UsageError

from ims import __version__ as version
from ims.config import Configuration, LogFormat


__all__ = ()


openFile = open



class Options(BaseOptions):
    """
    Options, cleaned up
    """

    def opt_version(self) -> None:
        """
        Print version and exit.
        """
        exit(ExitStatus.EX_OK, f"{version}")



class ServerOptions(Options):
    """
    Command line options for the IMS server.
    """



class ExportOptions(Options):
    """
    Command line options for the IMS server.
    """



class IMSOptions(Options):
    """
    Command line options for all IMS commands.
    """

    log: ClassVar[Logger] = Logger()
    defaultLogLevel: ClassVar = LogLevel.info

    subCommands: ClassVar = [
        ["server", None, ServerOptions, "Run the IMS server"],
        ["export", None, ExportOptions, "Export data"],
    ]
    # defaultSubCommand = "server"


    def getSynopsis(self) -> str:
        return f"{Options.getSynopsis(self)} command [command_options]"


    def opt_config(self, path: str) -> None:
        """
        Location of configuration file.
        """
        cast(MutableMapping, self)["configFile"] = Path(path)


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
            f'"{l.name}"' for l in LogLevel.iterconstants()
        ),
        default=defaultLogLevel.name,
    )


    def opt_log_file(self, fileName: str) -> None:
        """
        Log to file. ("-" for stdout, "+" for stderr; default: "-")
        """
        self["logFileName"] = fileName


    def opt_log_format(self, logFormatName: str) -> None:
        """
        Log file format.
        (options: "text", "json"; default: "text" if the log file is a tty,
        otherwise "json")
        """
        try:
            logFormat = LogFormat[logFormatName.lower()]
        except KeyError:
            raise UsageError(f"Invalid log format: {logFormatName}")

        if logFormat is LogFormat.text:
            self["fileLogObserverFactory"] = textFileLogObserver
        elif logFormat is LogFormat.json:
            self["fileLogObserverFactory"] = jsonFileLogObserver
        else:
            raise AssertionError(f"Unhandled LogFormat: {logFormat}")

        self["logFormat"] = logFormat

    opt_log_format.__doc__ = dedent(cast(str, opt_log_format.__doc__))


    def opt_option(self, arg: str) -> None:
        """
        Set a configuration option.
        Format is "[section]name=value", eg: "[Core]Host=0.0.0.0".
        """
        try:
            if arg.startswith("["):
                section, rest = arg[1:].split("]", 1)
            else:
                section = "Core"
                rest = arg
            name, value = rest.split("=", 1)
        except ValueError:
            raise UsageError(f"Invalid option specifier: {arg}")

        if "overrides" not in self:
            self["overrides"] = []

        self["overrides"].append(
            Override(section=section, name=name, value=value)
        )


    def initConfig(self) -> None:
        try:
            configFile = cast(
                Optional[Path], cast(Mapping, self).get("configFile")
            )

            if configFile and not configFile.is_file():
                self.log.info("Config file not found.")
                configFile = None

            configuration = Configuration.fromConfigFile(configFile)

            options = cast(MutableMapping, self)

            if "overrides" in options:
                for _override in options["overrides"]:
                    raise NotImplementedError("Option overrides unimplemented")

            if "logFileName" in options:
                configuration = configuration.replace(
                    logFilePath=Path(options["logFileName"])
                )

            self.opt_log_file(str(configuration.logFilePath))

            if "logFormat" in options:
                configuration = configuration.replace(
                    logFormat=options["logFormat"]
                )
            elif configuration.logFormat is not None:
                self.opt_log_format(configuration.logFormat.name)

            if "logLevel" in options:
                configuration = configuration.replace(
                    logLevelName=options["logLevel"].name
                )
            elif configuration.logLevelName is not None:
                self.opt_log_level(configuration.logLevelName)

            options["configuration"] = configuration

        except Exception as e:
            exit(ExitStatus.EX_CONFIG, str(e))


    def initLogFile(self) -> None:
        fileName = self["logFileName"]

        logFile: IO
        if fileName == "-":
            logFile = stdout
        elif fileName == "+":
            logFile = stderr
        else:
            try:
                logFile = openFile(fileName, "a")
            except EnvironmentError as e:
                exit(
                    ExitStatus.EX_IOERR,
                    f"Unable to open log file {fileName!r}: {e}"
                )

        self["logFileName"] = logFile


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

        self.initLogFile()
        self.selectDefaultLogObserver()


    def postOptions(self) -> None:
        Options.postOptions(self)

        self.initConfig()



@attrs(frozen=True, auto_attribs=True, kw_only=True)
class Override(object):
    """
    Configuration option override.
    """

    section: str
    name: str
    value: str
