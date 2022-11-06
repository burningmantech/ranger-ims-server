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

from collections.abc import Mapping, MutableMapping, Sequence
from pathlib import Path
from sys import stderr, stdin, stdout
from textwrap import dedent
from typing import IO, Any, ClassVar, Optional, cast

from attrs import frozen
from twisted.application.runner._exit import ExitStatus, exit
from twisted.logger import (
    InvalidLogLevelError,
    Logger,
    LogLevel,
    jsonFileLogObserver,
    textFileLogObserver,
)
from twisted.python.usage import Options as BaseOptions
from twisted.python.usage import UsageError

from ims import __version__ as version
from ims.config import Configuration, LogFormat


__all__ = ()


def openFile(fileName: str, mode: str) -> IO[Any]:
    """
    Open a file, given a name.
    Handles "+" and "-" as stdin/stdout.
    """
    file: IO[Any]

    def openNamedFile() -> IO[Any]:
        try:
            file = open(fileName, mode)
        except OSError as e:
            exit(ExitStatus.EX_IOERR, f"Unable to open file {fileName!r}: {e}")
        return file

    if any((c in mode) for c in "wxa"):
        if fileName == "-":
            file = stdout
        elif fileName == "+":
            file = stderr
        else:
            file = openNamedFile()
    else:
        if fileName == "-":
            file = stdin
        else:
            file = openNamedFile()

    return file


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
    Command line options for the IMS export tool.
    """

    def opt_output(self, fileName: str) -> None:
        """
        Output file. ("-" for stdout, "+" for stderr; default: "-")
        """
        self["outFile"] = openFile(fileName, "wb")


class ImportOptions(Options):
    """
    Command line options for the IMS import tool.
    """

    def opt_input(self, fileName: str) -> None:
        """
        Input file. ("-" for stdin)
        """
        self["inFile"] = openFile(fileName, "rb")


class CompareOptions(Options):
    """
    Command line options for the IMS export comparison tool.
    """

    def parseArgs(self, *fileNames: str) -> None:
        """
        Input files. ("-" for stdin)
        """
        files = []

        for fileName in fileNames:
            files.append(openFile(fileName, "rb"))

        self["inFiles"] = files


class HashPasswordOptions(Options):
    """
    Command line options for the IMS export comparison tool.
    """

    def parseArgs(self, password: str) -> None:  # type: ignore[override]
        """
        Handle password.
        """
        self["password"] = password


class VerifyPasswordOptions(Options):
    """
    Command line options for the IMS export comparison tool.
    """

    def parseArgs(  # type: ignore[override]
        self, password: str, hashedPassword: str
    ) -> None:
        """
        Handle password.
        """
        self["password"] = password
        self["hashedPassword"] = hashedPassword


class IMSOptions(Options):
    """
    Command line options for all IMS commands.
    """

    log: ClassVar[Logger] = Logger()
    defaultLogLevel: ClassVar = LogLevel.info

    subCommands: ClassVar = [
        ["server", None, ServerOptions, "Run the IMS server"],
        ["export", None, ExportOptions, "Export data"],
        ["import", None, ImportOptions, "Import data"],
        ["export_compare", None, CompareOptions, "Compare two export files"],
        ["hash_password", None, HashPasswordOptions, "Hash a password"],
        ["verify_password", None, VerifyPasswordOptions, "Verify a password"],
    ]

    def getSynopsis(self) -> str:
        return f"{Options.getSynopsis(self)} command [command_options]"

    def opt_config(self, path: str) -> None:
        """
        Location of configuration file.
        """
        cast(MutableMapping[str, Any], self)["configFile"] = Path(path)

    def opt_log_level(self, levelName: str) -> None:
        """
        Set default log level.
        (options: {options}; default: "{default}")
        """
        try:
            self["logLevel"] = LogLevel.levelWithName(levelName)
        except InvalidLogLevelError as e:
            raise UsageError(f"Invalid log level: {levelName}") from e

    opt_log_level.__doc__ = dedent(cast(str, opt_log_level.__doc__)).format(
        options=", ".join(
            f'"{level.name}"' for level in LogLevel.iterconstants()
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
            raise UsageError(f"Invalid log format: {logFormatName}") from None

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
            raise UsageError(f"Invalid option specifier: {arg}") from None

        if "overrides" not in self:
            self["overrides"] = []

        self["overrides"].append(
            Override(section=section, name=name, value=value)
        )

    def initConfig(self) -> None:
        try:
            configFile = cast(
                Optional[Path], cast(Mapping[str, Any], self).get("configFile")
            )

            if configFile and not configFile.is_file():
                self.log.info("Config file not found.")
                configFile = None

            configuration = Configuration.fromConfigFile(configFile)

            options = cast(MutableMapping[str, Any], self)

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
        self["logFile"] = openFile(self["logFileName"], "a")

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

    def parseOptions(self, options: Sequence[str] | None = None) -> None:
        super().parseOptions(options=options)

        self.initLogFile()
        self.selectDefaultLogObserver()

    def postOptions(self) -> None:
        super().postOptions()

        if self.subCommand is None:
            raise UsageError("No subcommand specified.")

        self.log.info("Running command: {command}...", command=self.subCommand)

        self.subOptions["stderr"] = stderr
        self.subOptions["stdin"] = stdin
        self.subOptions["stdout"] = stdout

        self.initConfig()


@frozen(kw_only=True)
class Override:
    """
    Configuration option override.
    """

    section: str
    name: str
    value: str
