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

from collections.abc import Iterable
from enum import Enum, unique
from typing import AbstractSet, Optional

from attr import attrib, attrs
from attr.validators import instance_of, optional

from ims.ext.attr import true

AbstractSet, Optional  # silence linter


__all__ = ()


statusDescriptions = dict(
    prospective="Prospective",
    alpha="Alpha",
    bonked="Bonked Prospective",
    active="Active Ranger",
    inactive="Inactive Ranger",
    retired="Retired Ranger",
    uberbonked="Uberbonked Participant",
    vintage="Vintage Ranger",
    deceased="Late Ranger",
)



@unique
class RangerStatus(Enum):
    """
    Ranger status

    A Ranger status denotes the status of a Ranger in the Ranger department.
    """

    prospective = 0
    alpha       = 1
    bonked      = 2
    active      = 3
    inactive    = 4
    retired     = 5
    uberbonked  = 6
    vintage     = 7
    deceased    = 8

    other = -1


    def __repr__(self) -> str:
        return "{}[{!r}]".format(self.__class__.__name__, self.name)


    def __str__(self) -> str:
        return statusDescriptions.get(
            self.name, "(Unknown Person Type: {})".format(self.name)
        )



@attrs(frozen=True)
class Ranger(object):
    """
    Ranger

    An Ranger contains information about a Black Rock Ranger; a person record
    specific to a Black Rock Ranger.
    """

    # FIXME: better validator for email

    handle: str = attrib(
        validator=true(instance_of(str))
    )
    name: str = attrib(
        validator=true(instance_of(str))
    )
    status: RangerStatus = attrib(
        validator=instance_of(RangerStatus)
    )
    email: AbstractSet[str] = attrib(
        validator=instance_of(Iterable), convert=frozenset
    )
    onSite: bool = attrib(
        validator=instance_of(bool)
    )
    dmsID: Optional[str] = attrib(
        validator=optional(instance_of(int))
    )
    password: Optional[str] = attrib(
        validator=optional(instance_of(str))
    )


    def __str__(self) -> str:
        return "{} {} ({})".format(self.status, self.handle, self.name)
