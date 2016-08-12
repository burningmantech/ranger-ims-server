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

from weakref import ref as WeakReference
from collections import deque

from zope.interface import implementer
from twisted.logger import ILogObserver, eventAsJSON
from twisted.web.server import NOT_DONE_YET
from twisted.web.resource import IResource

from .http import HeaderName, ContentType



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

        if self.eventRetry is not None:
            parts.append(u"retry: {0:d}".format(self.eventRetry))

        parts.extend(
            u"data: {}".format(line) for line in self.text.split(u"\n")
        )

        return (u"\n".join(parts) + u"\n\n").encode("utf-8")



@implementer(ILogObserver)
class DataStoreLogObserver(object):
    """
    Observer for events related to any incident changing.
    """
    def __init__(self):
        self._listeners = set()
        self._expiredListeners = set()

        self._events = deque(maxlen=1000)


    def addListener(self, listener):
        ref = WeakReference(listener, self._expiredListeners.add)
        self._listeners.add(ref)


    def renderEvent(self, loggerEvent):
        eventSourceEvent = Event(
            eventClass="Store Write",
            message=eventAsJSON(loggerEvent),
        )
        return eventSourceEvent.render()


    def __call__(self, event):
        if "storeWriteClass" not in event:
            return

        eventText = self.renderEvent(event)

        # Clean up, expired listeners
        for ref in self._expiredListeners:
            self._listeners.remove(ref)

        for ref in self._listeners:
            listener = ref()
            if listener is None:
                self._expiredListeners.add(ref)
                continue

            listener.notify(eventText)



@implementer(IResource)
class DataStoreEventSourceResource(object):
    """
    Event source for data store changes.
    """
    def __init__(self, observer):
        self.observer = observer


    def notify(self, event):
        self.request.write(event.render())


    def render(self, request):
        request.setHeader(
            HeaderName.contentType.value, ContentType.eventStream.value
        )
        self.observer.addListener(self)
        return NOT_DONE_YET
