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
Tests for :mod:`ranger-ims-server.model.json._state`
"""

from hypothesis import given

from ims.ext.trial import TestCase

from ..._state import IncidentState
from ...strategies import incidentStates
from .._json import jsonDeserialize, jsonSerialize
from .json import jsonFromIncidentState


__all__ = ()


class IncidentStateSerializationTests(TestCase):
    """
    Tests for serialization of :class:`IncidentState`
    """

    @given(incidentStates())
    def test_serialize(self, state: IncidentState) -> None:
        """
        :func:`jsonSerialize` serializes the given incident state as
        the expected value.
        """
        self.assertEqual(jsonSerialize(state), jsonFromIncidentState(state))


class IncidentStateDeserializationTests(TestCase):
    """
    Tests for deserialization of :class:`IncidentState`
    """

    @given(incidentStates())
    def test_deserialize(self, state: IncidentState) -> None:
        """
        :func:`jsonDeserialize` returns the expected incident state for the
        given value.
        """
        self.assertIdentical(
            jsonDeserialize(jsonFromIncidentState(state), IncidentState), state
        )
