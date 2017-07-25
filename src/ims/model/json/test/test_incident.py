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
Tests for :mod:`ranger-ims-server.model.json._incident`
"""

from hypothesis import given

from ims.ext.trial import TestCase

from .json import jsonFromIncident
from .._json import jsonDeserialize, jsonSerialize
from ..._incident import Incident
from ...strategies import incidents


__all__ = ()



class IncidentSerializationTests(TestCase):
    """
    Tests for serialization of :class:`Incident`
    """

    @given(incidents())
    def test_serialize(self, incident: Incident) -> None:
        """
        :func:`jsonSerialize` serializes the given incident.
        """
        self.assertEqual(jsonSerialize(incident), jsonFromIncident(incident))



class IncidentDeserializationTests(TestCase):
    """
    Tests for deserialization of :class:`Incident`
    """

    @given(incidents())
    def test_deserialize(self, incident: Incident) -> None:
        """
        :func:`jsonDeserialize` returns an incident with the correct data.
        """
        self.assertEqual(
            jsonDeserialize(jsonFromIncident(incident), Incident), incident
        )
