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
JSON export command line.
"""

import sys
from sys import stdout
from typing import Sequence

from attr import attrs

from twisted.application.runner._exit import ExitStatus, exit
from twisted.application.runner._runner import Runner
from twisted.internet.defer import ensureDeferred
from twisted.logger import Logger
from twisted.python.usage import UsageError

from ims.config import Configuration
from ims.run._server._options import ServerOptions

from ._export import JSONExporter

__all__ = ()



class JSONExportOptions(ServerOptions):
    """
    Command line options for the JSON export command.
    """



@attrs(frozen=True, auto_attribs=True, kw_only=True)
class JSONExportCommand(object):
    """
    JSON export command.
    """

    log = Logger()


    @staticmethod
    def options(argv: Sequence[str]) -> JSONExportOptions:
        """
        Parse command line options.
        """
        options = JSONExportOptions()

        try:
            options.parseOptions(argv[1:])
        except UsageError as e:
            exit(ExitStatus.EX_USAGE, f"Error: {e}\n\n{options}")

        return options


    @classmethod
    def whenRunning(cls, options: JSONExportOptions) -> None:
        """
        Called after the reactor has started.
        """
        config: Configuration = options["configuration"]

        from twisted.internet import reactor

        async def run() -> None:
            try:
                await config.store.upgradeSchema()
                await config.store.validate()

                exporter = JSONExporter(store=config.store)
                data = await exporter.asBytes()

                print(data)
            except Exception:
                cls.log.failure("Unable to export data")

            reactor.stop()

        return ensureDeferred(run())


    @classmethod
    def run(cls, options: ServerOptions) -> None:
        """
        Run the application service.
        """
        from twisted.internet import reactor

        runner = Runner(
            reactor=reactor,
            defaultLogLevel=options.get("logLevel", options.defaultLogLevel),
            logFile=options.get("logFile", stdout),
            fileLogObserverFactory=options["fileLogObserverFactory"],
            whenRunning=cls.whenRunning,
            whenRunningArguments=dict(options=options),
        )
        runner.run()


    @classmethod
    def main(cls, argv: Sequence[str] = sys.argv) -> None:
        """
        Executable entry point for :class:`Server`.
        Processes options and run a twisted reactor with a service.
        """
        cls.run(cls.options(argv))
