# -*- test-case-name: ranger-ims-server.model.test.test_priority -*-

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
Incident priority
"""

from ims.ext.enum_ext import Names, auto, enumOrdering


__all__ = ()


@enumOrdering
class IncidentPriority(Names):
    """
    Incident priorities

    Priorities are used to denote the relative urgency of resolving a
    particular incident.
    """

    high = auto()
    normal = auto()
    low = auto()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}[{self.name!r}]"

    def __str__(self) -> str:
        return self.name
