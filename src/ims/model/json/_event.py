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

from typing import Type

from ._json import registerDeserializer, registerSerializer
from .._event import Event


__all__ = ()


def serializeEvent(event: Event) -> str:
    return event.id


registerSerializer(Event, serializeEvent)


def deserializeEvent(cl: Type, obj: str) -> Event:
    assert cl is Event, (cl, obj)

    return Event(id=obj)


registerDeserializer(Event, deserializeEvent)
