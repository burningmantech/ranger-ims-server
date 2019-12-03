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
Tests for :mod:`ranger-ims-server.model._type`
"""

from hypothesis import assume, given
from hypothesis.strategies import booleans, sampled_from

from ims.ext.trial import TestCase

from .._type import IncidentType, KnownIncidentType, knownIncidentTypeNames
from ..strategies import incidentTypes


__all__ = ()


class IncidentTypeTests(TestCase):
    """
    Tests for :class:`IncidentType`
    """

    @given(incidentTypes(), booleans())
    def test_known_unknown(
        self, incidentType: IncidentType, hidden: bool
    ) -> None:
        """
        The Unknown Knowns are known.
        """
        assume(incidentType.name not in knownIncidentTypeNames)

        self.assertFalse(incidentType.known())

    @given(sampled_from(KnownIncidentType), booleans())
    def test_known_known(
        self, knownType: KnownIncidentType, hidden: bool
    ) -> None:
        """
        The Known Knowns are known.
        """
        incidentType = IncidentType(name=knownType.value, hidden=hidden)
        self.assertTrue(incidentType.known())
