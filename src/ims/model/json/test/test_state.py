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

from .._json import jsonDeserialize, jsonSerialize
from ..._state import IncidentState
from ....ext.trial import TestCase


__all__ = ()



incidentStateToJSON = {
    IncidentState.new: "new",
    IncidentState.onHold: "on_hold",
    IncidentState.dispatched: "dispatched",
    IncidentState.onScene: "on_scene",
    IncidentState.closed: "closed",
}



class IncidentStateSerializationTests(TestCase):
    """
    Tests for serialization of :class:`IncidentState`
    """

    def test_serialize(self) -> None:
        """
        :func:`jsonSerialize` serializes the given incident state as
        the expected value.
        """
        for incidentState, jsonValue in incidentStateToJSON.items():
            self.assertEqual(jsonSerialize(incidentState), jsonValue)



class IncidentStateDeserializationTests(TestCase):
    """
    Tests for deserialization of :class:`IncidentState`
    """

    def test_deserialize(self) -> None:
        """
        :func:`jsonDeserialize` returns the expected incident state for the
        given value.
        """
        for incidentState, jsonValue in incidentStateToJSON.items():
            self.assertIdentical(
                jsonDeserialize(jsonValue, IncidentState),
                incidentState
            )
