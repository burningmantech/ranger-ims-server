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
from hypothesis.strategies import text


from .._json import jsonDeserialize, jsonSerialize
from ..._event import Event
from ....ext.trial import TestCase


__all__ = ()



class EventSerializationTests(TestCase):
    """
    Tests for serialization of :class:`Event`
    """

    @given(text(min_size=1))
    def test_serialize(self, eventID: str) -> None:
        """
        :func:`jsonSerialize` serializes the given event using its ID.
        """
        self.assertEqual(jsonSerialize(Event(id=eventID)), eventID)



class EventDeserializationTests(TestCase):
    """
    Tests for deserialization of :class:`Event`
    """

    @given(text(min_size=1))
    def test_deserialize(self, eventID: str) -> None:
        """
        :func:`jsonDeserialize` returns an event with an ID corresponding to
        the given value.
        """
        self.assertEqual(
            jsonDeserialize(eventID, Event),
            Event(id=eventID),
        )
