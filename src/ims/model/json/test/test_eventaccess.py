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
Tests for :mod:`ranger-ims-server.model.json._eventaccess`
"""

from hypothesis import given

from ims.ext.trial import TestCase

from .json import jsonFromEventAccess
from .._json import jsonDeserialize, jsonSerialize
from ..._eventaccess import EventAccess
from ...strategies import eventAccesses


__all__ = ()



class EventAccessSerializationTests(TestCase):
    """
    Tests for serialization of :class:`EventAccess`
    """

    @given(eventAccesses())
    def test_serialize(self, eventAccess: EventAccess) -> None:
        """
        :func:`jsonSerialize` serializes the given event data.
        """
        self.assertEqual(
            jsonSerialize(eventAccess), jsonFromEventAccess(eventAccess)
        )



class EventAccessDeserializationTests(TestCase):
    """
    Tests for deserialization of :class:`EventAccess`
    """

    @given(eventAccesses())
    def test_deserialize(self, eventAccess: EventAccess) -> None:
        """
        :func:`jsonDeserialize` returns an EventAccess with the correct data.
        """
        self.assertEqual(
            jsonDeserialize(jsonFromEventAccess(eventAccess), EventAccess),
            eventAccess
        )
