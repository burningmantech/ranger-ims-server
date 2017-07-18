# -*- test-case-name: ranger-ims-server.model.test.test_address -*-

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
Address
"""

from abc import ABC
from typing import Any, Optional, TypeVar

from attr import attrib, attrs
from attr.validators import instance_of, optional

from ._cmp import ComparisonMixIn
from ._replace import ReplaceMixIn

Optional  # Silence linter


__all__ = ()


TRodGarettAddress = TypeVar("TRodGarettAddress", bound="RodGarettAddress")



class Address(ABC):
    """
    Location address
    """

    description: Optional[str]



@attrs(frozen=True, cmp=False)
class TextOnlyAddress(Address, ComparisonMixIn):
    """
    Address

    An address contains a description of a location.
    """

    description: Optional[str] = attrib(
        validator=optional(instance_of(str)), default=None
    )


    def _cmpValue(self) -> Any:
        return self.description



@attrs(frozen=True, cmp=False)
class RodGarettAddress(Address, ComparisonMixIn, ReplaceMixIn):
    """
    Rod Garett Address

    Address at concentric and radial streets, as per Rod Garett's design for
    Black Rock City.
    """

    description: Optional[str] = attrib(
        validator=optional(instance_of(str)), default=None
    )
    concentric: Optional[str] = attrib(
        validator=optional(instance_of(str)), default=None
    )
    radialHour: Optional[int] = attrib(
        validator=optional(instance_of(int)), default=None
    )
    radialMinute: Optional[int] = attrib(
        validator=optional(instance_of(int)), default=None
    )


    def _cmpValue(self) -> Any:
        return (
            self.concentric, self.radialHour, self.radialMinute,
            self.description,
        )


    def _cmp(self, other: Any, methodName: str) -> bool:
        if other.__class__ is TextOnlyAddress:
            if (
                self.concentric is None and
                self.radialHour is None and
                self.radialMinute is None
            ):
                return getattr(self.description, methodName)(other.description)

        return ComparisonMixIn._cmp(self, other, methodName)


    def __hash__(self) -> int:
        if (
            self.concentric is None and
            self.radialHour is None and
            self.radialMinute is None
        ):
            return hash(self.description)

        return ComparisonMixIn.__hash__(self)
