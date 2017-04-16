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
Tests for :mod:`ranger-ims-server.model._event`
"""

from twisted.python.compat import cmp

from .._event import Event
from ...ext.trial import TestCase


__all__ = ()



class EventTests(TestCase):
    """
    Tests for :class:`Event`
    """

    def test_ordering(self) -> None:
        """
        Event ordering corresponds to event ID ordering.
        """
        for idA, idB in (("a", "b"), ("b", "a")):
            eventA = Event(id=idA)
            eventB = Event(id=idB)

            self.assertEqual(cmp(idA, idB), cmp(eventA, eventB))
