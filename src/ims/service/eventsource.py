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
HTML5 EventSource support.
"""

from collections import deque
from time import time

from zope.interface import implementer
from twisted.logger import Logger, ILogObserver

from ..data.model import Incident
from ..data.json import jsonTextFromObject



class Event(object):
    """
    HTML5 EventSource event.
    """
    def __init__(self, message, eventID=None, eventClass=None, retry=None):
        self.message    = message
        self.eventID    = eventID
        self.eventClass = eventClass
        self.retry      = retry


    def render(self):
        parts = []

        if self.eventID is not None:
            parts.append("id: {0}".format(self.eventID))

        if self.eventClass is not None:
            parts.append("event: {0}".format(self.eventClass))

        if self.retry is not None:
            parts.append("retry: {0:d}".format(self.retry))

        parts.extend(
            "data: {}".format(line) for line in self.message.split("\n")
        )

        return ("\r\n".join(parts) + "\r\n\r\n")



@implementer(ILogObserver)
class DataStoreEventSourceLogObserver(object):
    """
    Observer for events related to any updates to the data store.
    """
    log = Logger()


    def __init__(self):
        self._listeners = set()
        self._events = deque(maxlen=1000)
        self._start = time()
        self._counter = 0


    def addListener(self, listener, lastEventID=None):
        self.log.debug("Adding listener: {listener}", listener=listener)

        self._playback(listener, lastEventID)

        self._listeners.add(listener)


    def removeListener(self, listener):
        self.log.debug("Removing listener: {listener}", listener=listener)

        self._listeners.add(listener)


    def _transmogrify(self, loggerEvent, eventID):
        """
        Convert a logger event into an EventSource event.
        """
        if "storeWriteClass" not in loggerEvent:
            # Not a data store event
            return None

        eventClass = loggerEvent.get("storeWriteClass", None)

        if eventClass is None:
            return

        elif eventClass is Incident:
            incident = loggerEvent.get("incident", None)

            if incident is None:
                incidentNumber = loggerEvent.get("incidentNumber", None)
            else:
                incidentNumber = incident.number

            if incidentNumber is None:
                self.log.critical(
                    "Unable to determine incident number from store event: "
                    "{event}",
                    event=loggerEvent,
                )
                return

            message = dict(incident_number=incidentNumber)

        else:
            self.log.debug(
                "Unknown data store event class: {eventClass}",
                eventClass=eventClass
            )
            return

        eventSourceEvent = Event(
            eventID=eventID,
            eventClass=eventClass.__name__,
            message=jsonTextFromObject(message),
        )
        return eventSourceEvent


    def _playback(self, listener, lastEventID):
        if lastEventID is None:
            return

        observerID, counter = lastEventID.split(":")

        if observerID != str(id(self)):
            # lastEventID came from a different observer
            counter = 0

        for eventCounter, event in self.events:
            if eventCounter >= counter:
                listener.write(event.render().encode("utf-8"))


    def _publish(self, eventSourceEvent, eventID):
        eventText = eventSourceEvent.render().encode("utf-8")

        for listener in tuple(self._listeners):
            try:
                listener.write(eventText)
            except Exception as e:
                self.log.error(
                    "Unable to publish to EventSource listener {listener}: "
                    "{error}",
                    listener=listener, error=e,
                )
                self.removeListener(listener)

        self._events.append((self._counter, eventSourceEvent))


    def __call__(self, event):
        self._counter += 1

        eventSourceEvent = self._transmogrify(event, self._counter)
        if eventSourceEvent is None:
            return

        self._publish(eventSourceEvent, self._counter)
