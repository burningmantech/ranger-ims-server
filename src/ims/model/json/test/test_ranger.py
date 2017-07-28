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
Tests for :mod:`ranger-ims-server.model.json._ranger`
"""

from hypothesis import given

from ims.ext.trial import TestCase

from .json import jsonFromRanger
from .._json import jsonDeserialize, jsonSerialize
from ..._ranger import Ranger
from ...strategies import rangers


__all__ = ()



class RangerSerializationTests(TestCase):
    """
    Tests for serialization of :class:`Ranger`
    """

    @given(rangers())
    def test_serialize(self, ranger: Ranger) -> None:
        """
        :func:`jsonSerialize` serializes the given Ranger.
        """
        self.assertEqual(jsonSerialize(ranger), jsonFromRanger(ranger))



class RangerDeserializationTests(TestCase):
    """
    Tests for deserialization of :class:`Ranger`
    """

    @given(rangers())
    def test_deserialize(self, ranger: Ranger) -> None:
        """
        :func:`jsonDeserialize` returns an Ranger with the correct data.
        """
        self.assertEqual(
            jsonDeserialize(jsonFromRanger(ranger), Ranger),
            ranger.replace(password=None),
        )
