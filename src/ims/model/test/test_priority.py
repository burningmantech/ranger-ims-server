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
Tests for :mod:`ranger-ims-server.model._entry`
"""

from ims.ext.trial import TestCase

from .._priority import IncidentPriority


__all__ = ()


class IncidentPriorityTests(TestCase):
    """
    Tests for :class:`IncidentPriority`
    """

    def test_repr(self) -> None:
        """
        Incident priority renders as a string.
        """
        for priority in IncidentPriority:
            self.assertEqual(
                repr(priority),
                f"{IncidentPriority.__name__}[{priority.name!r}]",
            )

    def test_str(self) -> None:
        """
        Incident priority renders as a string.
        """
        for priority in IncidentPriority:
            self.assertEqual(str(priority), priority.name)
