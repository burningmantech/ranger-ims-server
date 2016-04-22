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
from twext.python.usage import Executable, Options as BaseOptions
from twisted.logger import Logger
from twisted.internet.defer import inlineCallbacks
from twisted.web.server import Site

from .service import WebService



class WebTool(Executable):
    """
    Incident Management System web service command line tool.
    """

    log = Logger()


    class Options(BaseOptions):
        optFlags = []

        optParameters = [
            ["port", "p", 8080, "Port to listen on."],
        ]


        def opt_config(self, path):
            """
            Location of configuration file.
            """
            self["ConfigFile"] = FilePath(path)


        def getSynopsis(self):
            return "{}".format(
                BaseOptions.getSynopsis(self)
            )


    @inlineCallbacks
    def whenRunning(self):
        service = WebService()

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
        yield
