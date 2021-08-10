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
Tests for :mod:`ranger-ims-server.model.json._imsdata`
"""

from hypothesis import given

from ims.ext.trial import TestCase

from ..._imsdata import IMSData
from ...strategies import imsDatas
from .._json import jsonDeserialize, jsonSerialize
from .json import jsonFromIMSData


__all__ = ()


class IMSDataSerializationTests(TestCase):
    """
    Tests for serialization of :class:`IMSData`
    """

    @given(imsDatas())
    def test_serialize(self, imsData: IMSData) -> None:
        """
        :func:`jsonSerialize` serializes the given event data.
        """
        self.assertEqual(jsonSerialize(imsData), jsonFromIMSData(imsData))


class IMSDataDeserializationTests(TestCase):
    """
    Tests for deserialization of :class:`IMSData`
    """

    @given(imsDatas())
    def test_deserialize(self, imsData: IMSData) -> None:
        """
        :func:`jsonDeserialize` returns an imsData with the correct data.
        """
        self.assertEqual(
            jsonDeserialize(jsonFromIMSData(imsData), IMSData), imsData
        )
