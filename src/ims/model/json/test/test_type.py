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
Tests for :mod:`ranger-ims-server.model.json._type`
"""

from hypothesis import given

from ims.ext.trial import TestCase

from ..._type import IncidentType, KnownIncidentType
from ...strategies import incidentTypes, knownIncidentTypes
from .._json import jsonDeserialize, jsonSerialize
from .json import jsonFromIncidentType, jsonFromKnownIncidentType


__all__ = ()


class IncidentTypeSerializationTests(TestCase):
    """
    Tests for serialization of :class:`IncidentType`
    """

    @given(incidentTypes())
    def test_serialize(self, incidentType: IncidentType) -> None:
        """
        :func:`jsonSerialize` serializes the given incident type as
        the expected value.
        """
        self.assertEqual(
            jsonSerialize(incidentType), jsonFromIncidentType(incidentType)
        )


class IncidentTypeDeserializationTests(TestCase):
    """
    Tests for deserialization of :class:`IncidentType`
    """

    @given(incidentTypes())
    def test_deserialize(self, incidentType: IncidentType) -> None:
        """
        :func:`jsonDeserialize` returns the expected incident type for the
        given value.
        """
        self.assertEqual(
            jsonDeserialize(jsonFromIncidentType(incidentType), IncidentType),
            incidentType,
        )


class KnownIncidentTypeSerializationTests(TestCase):
    """
    Tests for serialization of :class:`KnownIncidentType`.
    """

    @given(knownIncidentTypes())
    def test_serialize(self, incidentType: KnownIncidentType) -> None:
        """
        :func:`jsonSerialize` returns the value of the given incident
        type.
        """
        self.assertEqual(
            jsonSerialize(incidentType), jsonFromKnownIncidentType(incidentType)
        )


class KnownIncidentTypeDeserializationTests(TestCase):
    """
    Tests for deserialization of :class:`KnownIncidentType`.
    """

    @given(knownIncidentTypes())
    def test_deserialize(self, incidentType: KnownIncidentType) -> None:
        """
        :func:`jsonDeserialize` returns the incident type with the given value.
        """
        self.assertIdentical(
            jsonDeserialize(
                jsonFromKnownIncidentType(incidentType), KnownIncidentType
            ),
            incidentType,
        )
