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
Tests for :mod:`ranger-ims-server.model.json._event`
"""

from hypothesis import given

from ims.ext.trial import TestCase

from .json import jsonFromEvent
from .strategies import events
from .._json import jsonDeserialize, jsonSerialize
from ..._event import Event


__all__ = ()



class EventSerializationTests(TestCase):
    """
    Tests for serialization of :class:`Event`
    """

    @given(events())
    def test_serialize(self, event: Event) -> None:
        """
        :func:`jsonSerialize` serializes the given event using its ID.
        """
        self.assertEqual(jsonSerialize(event), jsonFromEvent(event))



class EventDeserializationTests(TestCase):
    """
    Tests for deserialization of :class:`Event`
    """

    @given(events())
    def test_deserialize(self, event: Event) -> None:
        """
        :func:`jsonDeserialize` returns an event with an ID corresponding to
        the given value.
        """
        self.assertEqual(jsonDeserialize(jsonFromEvent(event), Event), event)
