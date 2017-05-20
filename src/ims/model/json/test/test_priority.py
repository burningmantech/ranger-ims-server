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
Tests for :mod:`ranger-ims-server.model.json._priority`
"""

from hypothesis import given

from .json import jsonFromIncidentPriority
from .strategies import incidentPriorities
from .._json import jsonDeserialize, jsonSerialize
from ..._priority import IncidentPriority
from ....ext.trial import TestCase


__all__ = ()



incidentPriorityToJSON = {
    IncidentPriority.high: 1,
    IncidentPriority.normal: 3,
    IncidentPriority.low: 5,
}



class IncidentPrioritySerializationTests(TestCase):
    """
    Tests for serialization of :class:`IncidentPriority`
    """

    @given(incidentPriorities())
    def test_serialize(self, priority: IncidentPriority) -> None:
        """
        :func:`jsonSerialize` serializes the given incident priority as the
        expected value.
        """
        self.assertEqual(
            jsonSerialize(priority), jsonFromIncidentPriority(priority)
        )



class IncidentPriorityDeserializationTests(TestCase):
    """
    Tests for deserialization of :class:`IncidentPriority`
    """

    @given(incidentPriorities())
    def test_deserialize(self, priority: IncidentPriority) -> None:
        """
        :func:`jsonDeserialize` returns the expected incident priority for the
        given value.
        """
        self.assertIdentical(
            jsonDeserialize(
                jsonFromIncidentPriority(priority), IncidentPriority
            ),
            priority
        )
