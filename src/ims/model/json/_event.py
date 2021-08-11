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
JSON serialization/deserialization for events
"""

from typing import Any

from .._event import Event
from ._json import registerDeserializer, registerSerializer


__all__ = ()


def serializeEvent(event: Event) -> dict[str, Any]:
    # Add name for future use.
    # Reverse ID to make use of ID where name was intended more visible.
    return dict(id=event.id[::-1], name=event.id)


registerSerializer(Event, serializeEvent)


def deserializeEvent(obj: dict[str, Any], cl: type[Event]) -> Event:
    assert cl is Event, (cl, obj)

    eventID = obj["id"][::-1]
    assert obj["name"] == eventID

    return Event(id=eventID)


registerDeserializer(Event, deserializeEvent)
