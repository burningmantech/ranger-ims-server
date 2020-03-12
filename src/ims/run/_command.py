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
from typing import ClassVar, List, Sequence

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
from ims.model.json import jsonObjectFromModelObject
from ims.store import IMSDataStore, StorageError
from ims.store.export import JSONExporter, JSONImporter

from ._log import patchCombinedLogFormatter
from ._options import CompareOptions, ExportOptions, IMSOptions, ImportOptions


__all__ = ()


class IMSSession(Session):
    sessionTimeout = 60 * 60 * 1  # 1 hour


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class Command(object):
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
            host=host,
            port=port,
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
        with options["outFile"] as outFile:
            exporter = JSONExporter(store=config.store)
            data = await exporter.asBytes()
            outFile.write(data)
        cls.stop()

    @classmethod
    async def runImport(
        cls, config: Configuration, options: ImportOptions
    ) -> None:
        with options["inFile"] as inFile:
            importer = JSONImporter.fromIO(store=config.store, io=inFile)
            await importer.storeData()
        cls.stop()

    @classmethod
    async def runCompare(
        cls, config: Configuration, options: CompareOptions
    ) -> None:
        importers = []  # type: List[JSONImporter]

        for inFile in options["inFiles"]:
            with inFile:
                cls.log.info("Reading export file...")
                importers.append(
                    JSONImporter.fromIO(store=config.store, io=inFile)
                )

        first = None

        for importer in importers:
            if first is None:
                first = importer
            else:
                cls.log.info("Comparing export files...")  # type: ignore[misc]

                imsDataA = first.imsData
                imsDataB = importer.imsData

                if imsDataA != imsDataB:

                    if imsDataA.incidentTypes != imsDataB.incidentTypes:
                        cls.log.error(
                            "Incident Types do not match: "
                            "{incidentTypesA} != {incidentTypesB}",
                            incidentTypesA=imsDataA.incidentTypes,
                            incidentTypesB=imsDataB.incidentTypes,
                        )

                    for eventDataA, eventDataB in zip(
                        sorted(imsDataA.events), sorted(imsDataB.events)
                    ):
                        if eventDataA.event != eventDataB.event:
                            cls.log.error(
                                "Events do not match: {eventsA} != {eventsB}",
                                eventsA=[e for e in imsDataA.events.event],
                                eventsB=[e for e in imsDataB.events.event],
                            )

                    for eventDataA, eventDataB in zip(
                        sorted(imsDataA.events), sorted(imsDataB.events)
                    ):
                        if eventDataA.access != eventDataB.access:
                            cls.log.error(
                                "Events ACLs do not match: {aclA} != {aclB}",
                                aclA=eventDataA.access,
                                aclB=eventDataB.access,
                            )

                        if (
                            eventDataA.concentricStreets
                            != eventDataB.concentricStreets
                        ):
                            cls.log.error(
                                "Events concentric streets do not match: "
                                "{streetsA} != {streetsB}",
                                streetsA=eventDataA.concentricStreets,
                                streetsB=eventDataB.concentricStreets,
                            )

                        if eventDataA.incidents != eventDataB.incidents:
                            cls.log.error(
                                "Events incidents do not match: {event}",
                                event=eventDataA.event,
                            )

                            numbersA = frozenset(
                                i.number for i in eventDataA.incidents
                            )
                            numbersB = frozenset(
                                i.number for i in eventDataB.incidents
                            )
                            if numbersA != numbersB:
                                cls.log.error(
                                    "Incident numbers do not match for event "
                                    "{event}",
                                    event=eventDataA.event,
                                )

                            for incidentA, incidentB in zip(
                                sorted(eventDataA.incidents),
                                sorted(eventDataB.incidents),
                            ):
                                if incidentA != incidentB:
                                    cls.log.error(
                                        "Incidents do not match for event "
                                        "{event}: {incidentA} != {incidentB}",
                                        event=eventDataA.event,
                                        incidentA=jsonObjectFromModelObject(
                                            incidentA
                                        ),
                                        incidentB=jsonObjectFromModelObject(
                                            incidentB
                                        ),
                                    )

                        if (
                            eventDataA.incidentReports
                            != eventDataB.incidentReports
                        ):
                            cls.log.error(
                                "Events incident reports do not match: "
                                "{event}",
                                event=eventDataA.event,
                            )

                    cls.log.error("Argh IMS data mismatch")

                    break

        cls.stop()

    @classmethod
    def whenRunning(cls, options: IMSOptions) -> Deferred:
        """
        Called after the reactor has started.
        """
        config: Configuration = options["configuration"]

        async def run() -> None:
            try:
                await cls.initStore(config.store)
            except StorageError as e:
                cls.log.critical(
                    "Unable to initialize data store: {error}", error=e
                )
                cls.stop()
                return

            subCommand = options.subCommand
            if subCommand is None:
                subCommand = "server"

            try:
                if subCommand == "server":
                    cls.runServer(config)
                elif subCommand == "export":
                    await cls.runExport(config, options.subOptions)
                elif subCommand == "import":
                    await cls.runImport(config, options.subOptions)
                elif subCommand == "compare":
                    await cls.runCompare(config, options.subOptions)
                else:
                    raise AssertionError(f"Unknown subcommand: {subCommand}")
            except BaseException as e:
                cls.log.critical(
                    "Unable to run {subCommand}: {error}",
                    subCommand=subCommand,
                    error=e,
                )
                cls.stop()
                return

        def error(f: Failure) -> None:
            cls.log.failure("Uncaught service error: {log_failure}", failure=f)
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
