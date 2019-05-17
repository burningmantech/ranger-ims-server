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
from typing import ClassVar, Deque, List, Mapping, Optional, Tuple

from attr import attrib, attrs

from twisted.logger import ILogObserver, Logger
from twisted.web.iweb import IRequest

from zope.interface import implementer

from ims.ext.json import jsonTextFromObject
from ims.model import Incident


__all__ = (
    "DataStoreEventSourceLogObserver",
)



@attrs(frozen=True, auto_attribs=True, kw_only=True)
class Event(object):
    """
    HTML5 EventSource event.
    """

    message: str
    eventID: Optional[int]
    eventClass: Optional[str]
    retry: Optional[int] = None


    def render(self) -> str:
        """
        Render this event as an HTML EventSource event.
        """
        parts = []

        if self.eventID is not None:
            parts.append(f"id: {self.eventID}")

        if self.eventClass is not None:
            parts.append(f"event: {self.eventClass}")

        if self.retry is not None:
            parts.append(f"retry: {self.retry}")

        parts.extend(
            f"data: {line}" for line in self.message.split("\n")
        )

        return ("\r\n".join(parts) + "\r\n\r\n")



@implementer(ILogObserver)
@attrs(frozen=True, auto_attribs=True, kw_only=True)
class DataStoreEventSourceLogObserver(object):
    """
    Observer for events related to any updates to the data store.
    """

    log: ClassVar = Logger()

    _listeners: List[IRequest] = attrib(init=False, factory=list)
    _events: Deque[Tuple[int, Event]] = attrib(
        init=False, factory=lambda: deque(maxlen=1000)
    )
    _start: float = attrib(init=False, factory=time)
    _counter: List[int] = attrib(init=False, factory=lambda: [0])


    def addListener(
        self, listener: IRequest, lastEventID: Optional[str] = None
    ) -> None:
        """
        Add a listener.
        """
        self.log.debug("Adding listener: {listener}", listener=listener)

        self._playback(listener, lastEventID)

        self._listeners.append(listener)


    def removeListener(self, listener: IRequest) -> None:
        """
        Remove a listener.
        """
        self.log.debug("Removing listener: {listener}", listener=listener)

        self._listeners.remove(listener)


    def _transmogrify(
        self, loggerEvent: Mapping, eventID: int
    ) -> Optional[Event]:
        """
        Convert a logger event into an EventSource event.
        """
        eventClass = loggerEvent.get("storeWriteClass", None)

        if eventClass is None:
            # Not a data store event
            return None

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
                return None

            message = dict(incident_number=incidentNumber)

        else:
            self.log.debug(
                "Unknown data store event class: {eventClass}",
                eventClass=eventClass
            )
            return None

        eventSourceEvent = Event(
            eventID=eventID,
            eventClass=eventClass.__name__,
            message=jsonTextFromObject(message),
        )
        return eventSourceEvent


    def _playback(
        self, listener: IRequest, lastEventID: Optional[str]
    ) -> None:
        if lastEventID is None:
            return

        observerID, counterString = lastEventID.split(":")

        if observerID == str(id(self)):
            counter = int(counterString)
        else:
            # lastEventID came from a different observer
            counter = 0

        for eventCounter, event in self._events:
            if eventCounter >= counter:
                listener.write(event.render().encode("utf-8"))


    def _publish(self, eventSourceEvent: Event, eventID: int) -> None:
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

        self._events.append((self._counter[0], eventSourceEvent))


    def __call__(self, event: Mapping) -> None:
        """
        See L{ILogObserver.__call__}.
        """
        self._counter[0] += 1

        eventSourceEvent = self._transmogrify(event, self._counter[0])
        if eventSourceEvent is None:
            return

        self._publish(eventSourceEvent, self._counter[0])
