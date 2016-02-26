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
Utilities
"""

__all__ = [
    "http_download",
]

from twisted.logger import Logger
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import Protocol
from twisted.web.client import Agent, ResponseDone

log = Logger()



def http_download(destination, url):
    """
    Download via HTTP.
    """
    class FileWriter(Protocol):
        def __init__(self, fp, fin):
            self.fp = fp
            self.tmp = fp.temporarySibling(".tmp")
            self.fh = self.tmp.open("w")
            self.fin = fin

        def dataReceived(self, bytes):
            self.fh.write(bytes)

        def connectionLost(self, reason):
            self.fh.close()
            if isinstance(reason.value, ResponseDone):
                self.tmp.moveTo(self.fp)
                self.fin.callback(None)
            else:
                self.fin.errback(reason)

    log.info(
        "Downloading from {url} to {destination}",
        url=url, destination=destination
    )

    agent = Agent(reactor)

    d = agent.request("GET", url)

    def gotResponse(response):
        finished = Deferred()
        response.deliverBody(FileWriter(destination, finished))
        return finished
    d.addCallback(gotResponse)
    return d
