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
Tests for :mod:`ranger-ims-server.model.json._json`
"""

from datetime import datetime as DateTime
from typing import Any

from hypothesis import given
from hypothesis.strategies import datetimes, floats, integers, text

from .strategies import incidents
from .._json import jsonDeserialize, jsonSerialize, jsonTextFromModelObject
from ..._incident import Incident
from ....ext.json import dateTimeAsRFC3339Text, jsonTextFromObject
from ....ext.trial import TestCase


__all__ = ()



class POPOSerializationTests(TestCase):
    """
    Tests for serialization of Plain Old Python Objects
    """

    def _test_identical(self, obj: Any) -> None:
        """
        :func:`jsonSerialize` serializes an object of the given type by
        returning the object itself.

        Use this only when expecting the identical object to be passed through
        as the return value, which is stricter than required for correctness,
        as returning an equal-but-different object is technically correct.

        The reason to use this is that returning the same object is a good
        optimization, so we want to notice if that behavior changes and find
        out why.
        """
        serialized = jsonSerialize(obj)

        self.assertIdentical(serialized, obj)


    def _test_equal(self, obj: Any) -> None:
        """
        :func:`jsonSerialize` serializes an object of the given type by
        returning and equal object of the same type.
        """
        serialized = jsonSerialize(obj)

        if serialized is obj:
            self.fail(
                "Serialized object is identical to input. "
                "Consider using _test_identical instead?"
            )

        self.assertIdentical(type(serialized), obj.__class__)
        self.assertEqual(serialized, obj)


    @given(text())
    def test_string(self, value: str) -> None:
        """
        :func:`jsonSerialize` correctly serializes a :class:`str`.
        """
        self._test_identical(value)


    @given(integers())
    def test_integer(self, value: int) -> None:
        """
        :func:`jsonSerialize` correctly serializes a :class:`int`.
        """
        self._test_identical(value)


    @given(floats(allow_nan=True, allow_infinity=True))
    def test_float(self, value: float) -> None:
        """
        :func:`jsonSerialize` correctly serializes a :class:`float`.
        """
        self._test_identical(value)


    @given(datetimes())
    def test_datetime(self, value: DateTime) -> None:
        """
        :func:`jsonSerialize` correctly serializes a :class:`DateTime`.
        """
        serialized = jsonSerialize(value)

        self.assertEqual(serialized, dateTimeAsRFC3339Text(value))



class POPODeserializationTests(TestCase):
    """
    Tests for deserialization of Plain Old Python Objects
    """

    def _test_identical(self, obj: Any) -> None:
        """
        :func:`jsonDeserialize` deserializes an object of the given type by
        returning the object itself.

        Use this only when expecting the identical object to be passed through
        as the return value, which is stricter than required for correctness,
        as returning an equal-but-different object is technically correct.

        The reason to use this is that returning the same object is a good
        optimization, so we want to notice if that behavior changes and find
        out why.
        """
        serialized = jsonSerialize(obj)
        assert serialized is obj  # Assumption, tested in serialization tests
        deserialized = jsonDeserialize(serialized, obj.__class__)
        self.assertIdentical(deserialized, obj)


    def _test_equal(self, obj: Any) -> None:
        """
        :func:`jsonDeserialize` deserializes an object of the given type by
        returning and equal object of the same type.
        """
        serialized = jsonSerialize(obj)
        deserialized = jsonDeserialize(serialized, obj.__class__)

        if deserialized is serialized:
            self.fail(
                "Deserialized object is identical to input. "
                "Consider using _test_identical instead?"
            )

        self.assertIdentical(type(deserialized), obj.__class__)
        self.assertEqual(deserialized, obj)


    @given(text())
    def test_string(self, value: str) -> None:
        """
        :func:`jsonDeserialize` correctly deserializes a :class:`str`.
        """
        self._test_identical(value)


    @given(integers())
    def test_integer(self, value: int) -> None:
        """
        :func:`jsonDeserialize` correctly deserializes a :class:`int`.
        """
        self._test_identical(value)


    @given(floats(allow_nan=True, allow_infinity=True))
    def test_float(self, value: float) -> None:
        """
        :func:`jsonDeserialize` correctly deserializes a :class:`float`.
        """
        self._test_identical(value)


    @given(datetimes())
    def test_datetime(self, value: DateTime) -> None:
        """
        :func:`jsonDeserialize` correctly deserializes a :class:`DateTime`.
        """
        self._test_equal(value)



class ModelSerializationTests(TestCase):
    """
    Tests for serialization of model objects
    """

    @given(incidents())
    def test_incident(self, incident: Incident) -> None:
        """
        :func:`jsonTextFromModelObject` serializes an incident as JSON text.
        """
        self.assertEqual(
            jsonTextFromModelObject(incident),
            jsonTextFromObject(jsonSerialize(incident))
        )
