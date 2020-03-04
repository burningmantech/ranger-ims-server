# -*- test-case-name: ranger-ims-server.model.test.test_ranger -*-

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
Position
"""

from typing import FrozenSet

from attr import attrs

from ._replace import ReplaceMixIn


__all__ = ()


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class Position(ReplaceMixIn):
    """
    Position

    A position is a role that a subset of Rangers can participate in during an
    event.
    """

    name: str
    members: FrozenSet[str]

    def __str__(self) -> str:
        return self.name
