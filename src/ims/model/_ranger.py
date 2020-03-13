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
Ranger
"""

from typing import FrozenSet, Optional

from attr import attrib, attrs

from ims.ext.enum import Names, auto, unique

from ._convert import freezeStrings
from ._replace import ReplaceMixIn


__all__ = ()


statusDescriptions = dict(
    active="Active Ranger",
    inactive="Inactive Ranger",
    vintage="Vintage Ranger",
    other="(Unknown Person Type)",
)


@unique
class RangerStatus(Names):
    """
    Ranger status

    A Ranger status denotes the status of a Ranger in the Ranger department.
    """

    active = auto()
    inactive = auto()
    vintage = auto()

    other = auto()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}[{self.name!r}]"

    def __str__(self) -> str:
        return statusDescriptions[self.name]


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class Ranger(ReplaceMixIn):
    """
    Ranger

    An Ranger contains information about a Black Rock Ranger; a person record
    specific to a Black Rock Ranger.
    """

    handle: str
    name: str
    status: RangerStatus
    email: FrozenSet[str] = attrib(converter=freezeStrings)
    enabled: bool
    directoryID: Optional[str]
    password: Optional[str] = None

    def __str__(self) -> str:
        return f"{self.status} {self.handle} ({self.name})"
