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
Run the IMS server.
"""

import sys
from sys import stdout
from typing import ClassVar, Sequence

from attr import attrs

from twisted.application.runner._exit import ExitStatus, exit
from twisted.application.runner._runner import Runner
from twisted.internet.defer import Deferred, ensureDeferred
from twisted.logger import Logger
from twisted.python.failure import Failure
from twisted.python.usage import UsageError
from twisted.web.server import Session, Site

from ims.application import Application
from ims.config import Configuration
from ims.store import IMSDataStore
from ims.store.export import JSONExporter

from ._log import patchCombinedLogFormatter
from ._options import ExportOptions, IMSOptions


__all__ = ()


class IMSSession(Session):
    sessionTimeout = 60 * 60 * 1  # 1 hour



@attrs(frozen=True, auto_attribs=True, kw_only=True)
class Server(object):
    """
    Run the IMS server.
    """

    log: ClassVar[Logger] = Logger()


    @staticmethod
    def options(argv: Sequence[str]) -> IMSOptions:
        """
        Parse command line options.
        """
        options = IMSOptions()

        try:
            options.parseOptions(argv[1:])
        except UsageError as e:
            exit(ExitStatus.EX_USAGE, f"Error: {e}\n\n{options}")

        return options


    @classmethod
    def stop(cls) -> None:
        from twisted.internet import reactor
        reactor.stop()


    @classmethod
    async def initStore(cls, store: IMSDataStore) -> None:
        await store.upgradeSchema()
        await store.validate()


    @classmethod
    def runServer(cls, config: Configuration) -> None:
        host = config.hostName
        port = config.port

        application = Application(config=config)

        cls.log.info(
            "Setting up web service at http://{host}:{port}/",
            host=host, port=port,
        )

        patchCombinedLogFormatter()

        factory = Site(application.router.resource())
        factory.sessionFactory = IMSSession

        from twisted.internet import reactor
        reactor.listenTCP(port, factory, interface=host)


    @classmethod
    async def runExport(
        cls, config: Configuration, options: ExportOptions
    ) -> None:
        exporter = JSONExporter(store=config.store)
        data = await exporter.asBytes()

        print(data.decode("utf-8"), file=options["outFile"])

        cls.stop()


    @classmethod
    def whenRunning(cls, options: IMSOptions) -> Deferred:
        """
        Called after the reactor has started.
        """
        config: Configuration = options["configuration"]

        async def run() -> None:
            await cls.initStore(config.store)

            if options.subCommand is None:
                cls.runServer(config)
            elif options.subCommand == "server":
                cls.runServer(config)
            elif options.subCommand == "export":
                await cls.runExport(config, options.subOptions)

        def error(f: Failure) -> None:
            cls.log.failure("Unable to start: {log_failure}", failure=f)
            cls.stop()

        d = ensureDeferred(run())
        d.addErrback(error)
        return d


    @classmethod
    def run(cls, options: IMSOptions) -> None:
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
