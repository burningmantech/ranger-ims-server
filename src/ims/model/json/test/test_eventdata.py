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
Tests for :mod:`ranger-ims-server.model.json._eventdata`
"""

from hypothesis import given

from ims.ext.trial import TestCase

from ..._eventdata import EventData
from ...strategies import eventDatas
from .._json import jsonDeserialize, jsonSerialize
from .json import jsonFromEventData


__all__ = ()


class EventDataSerializationTests(TestCase):
    """
    Tests for serialization of :class:`EventData`
    """

    @given(eventDatas())
    def test_serialize(self, eventData: EventData) -> None:
        """
        :func:`jsonSerialize` serializes the given event data.
        """
        self.assertEqual(jsonSerialize(eventData), jsonFromEventData(eventData))


class EventDataDeserializationTests(TestCase):
    """
    Tests for deserialization of :class:`EventData`
    """

    @given(eventDatas())
    def test_deserialize(self, eventData: EventData) -> None:
        """
        :func:`jsonDeserialize` returns an eventData with the correct data.
        """
        self.assertEqual(
            jsonDeserialize(jsonFromEventData(eventData), EventData), eventData
        )
