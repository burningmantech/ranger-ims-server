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

from ..ext.attr import attrib, attrs, instanceOf, optional, true

AbstractSet, Optional  # silence linter


__all__ = ()



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



@attrs(frozen=True)
class Ranger(object):
    """
    Ranger

    An Ranger contains information about a Black Rock Ranger; a person record
    specific to a Black Rock Ranger.
    """

    # FIXME: better validator for email

    handle = attrib(
        validator=true(instanceOf(str))
    )  # type: str
    name = attrib(
        validator=true(instanceOf(str))
    )  # type: str
    status = attrib(
        validator=instanceOf(RangerStatus)
    )  # type: RangerStatus
    email = attrib(
        validator=instanceOf(Iterable), convert=frozenset
    )  # type: AbstractSet
    onSite = attrib(
        validator=instanceOf(bool)
    )  # type: bool
    dmsID = attrib(
        validator=optional(instanceOf(int))
    )  # type: Optional[str]
    password = attrib(
        validator=optional(instanceOf(str))
    )  # type: Optional[str]
