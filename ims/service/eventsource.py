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

from zope.interface import implementer

from twisted.logger import Logger, ILogObserver, eventAsJSON



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
            parts.append(u"id: {0}".format(self.eventID))

        if self.eventClass is not None:
            parts.append(u"event: {0}".format(self.eventClass))

        if self.retry is not None:
            parts.append(u"retry: {0:d}".format(self.retry))

        parts.extend(
            u"data: {}".format(line) for line in self.message.split(u"\n")
        )

        return (u"\r\n".join(parts) + u"\r\n\r\n")



@implementer(ILogObserver)
class DataStoreEventSourceLogObserver(object):
    """
    Observer for events related to any updates to the data store.
    """
    log = Logger()


    def __init__(self):
        self._listeners = set()
        self._events = deque(maxlen=1000)


    def addListener(self, listener):
        self.log.debug("Adding listener: {listener}", listener=listener)

        # FIXME: send buffered events
        self._listeners.add(listener)


    def removeListener(self, listener):
        self.log.debug("Removing listener: {listener}", listener=listener)

        self._listeners.add(listener)


    def _transmogrify(self, loggerEvent):
        """
        Convert a logger event into an EventSource event.
        """
        if "storeWriteClass" not in loggerEvent:
            # Not a data store event
            return None

        eventSourceEvent = Event(
            # FIXME: add ID
            eventClass="Store Write",
            message=eventAsJSON(loggerEvent),
        )
        return eventSourceEvent


    def _publish(self, eventSourceEvent):
        eventText = eventSourceEvent.render().encode("utf-8")

        for listener in self._listeners:
            listener.write(eventText)

        self._events.append(eventText)


    def __call__(self, event):
        eventSourceEvent = self._transmogrify(event)
        if eventSourceEvent is None:
            return

        self._publish(eventSourceEvent)
