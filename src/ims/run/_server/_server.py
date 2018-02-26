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
from typing import Sequence

from twisted.application.runner._exit import ExitStatus, exit
from twisted.application.runner._runner import Runner
from twisted.logger import Logger
from twisted.python.usage import UsageError
from twisted.web.server import Session, Site

from ims.application import Application
from ims.config import Configuration

from ._log import patchCombinedLogFormatter
from ._options import ServerOptions


__all__ = ()


class IMSSession(Session):
    sessionTimeout = 60 * 60 * 1  # 1 hour



class Server(object):
    """
    Run the IMS server.
    """

    log = Logger()


    @staticmethod
    def options(argv: Sequence[str]) -> ServerOptions:
        """
        Parse command line options.
        """
        options = ServerOptions()

        try:
            options.parseOptions(argv[1:])
        except UsageError as e:
            exit(ExitStatus.EX_USAGE, f"Error: {e}\n\n{options}")

        return options


    @classmethod
    def whenRunning(cls, config: Configuration) -> None:
        """
        Called after the reactor has started.
        """
        config.store.upgradeSchema()
        config.store.validate()

        host = config.HostName
        port = config.Port

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
    def run(cls, options: ServerOptions) -> None:
        """
        Run the application service.
        """
        config = options["configuration"]

        from twisted.internet import reactor

        runner = Runner(
            reactor=reactor,
            defaultLogLevel=options.get("logLevel", options.defaultLogLevel),
            logFile=options.get("logFile", stdout),
            fileLogObserverFactory=options["fileLogObserverFactory"],
            whenRunning=cls.whenRunning,
            whenRunningArguments=dict(config=config),
        )
        runner.run()


    @classmethod
    def main(cls, argv: Sequence[str] = sys.argv) -> None:
        """
        Executable entry point for :class:`Server`.
        Processes options and run a twisted reactor with a service.
        """
        cls.run(cls.options(argv))
