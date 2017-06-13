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
from typing import Any, Optional

from attr import attrib, attrs
from attr.validators import instance_of, optional

Optional  # Silence linter


__all__ = ()



class Address(ABC):
    """
    Location address
    """

    description: str



@attrs(frozen=True, cmp=False)
class TextOnlyAddress(Address):
    """
    Address

    An address contains a description of a location.
    """

    description = attrib(validator=instance_of(str))  # type: str


    def _cmpValue(self) -> Any:
        return self.description


    def _cmp(self, other: Any, methodName: str) -> bool:
        if other.__class__ is self.__class__:
            selfValue = self._cmpValue()
            otherValue = other._cmpValue()
            selfValueCmp = getattr(selfValue, methodName)
            return selfValueCmp(otherValue)

        return NotImplemented


    def __hash__(self) -> int:
        return hash(self._cmpValue())


    def __eq__(self, other: Any) -> bool:
        return self._cmp(other, "__eq__")


    def __ne__(self, other: Any) -> bool:
        return self._cmp(other, "__ne__")


    def __lt__(self, other: Any) -> bool:
        return self._cmp(other, "__lt__")


    def __le__(self, other: Any) -> bool:
        return self._cmp(other, "__le__")


    def __gt__(self, other: Any) -> bool:
        return self._cmp(other, "__gt__")


    def __ge__(self, other: Any) -> bool:
        return self._cmp(other, "__ge__")



@attrs(frozen=True, cmp=False)
class RodGarettAddress(Address):
    """
    Rod Garett Address

    Address at concentric and radial streets, as per Rod Garett's design for
    Black Rock City.
    """

    description = attrib(
        validator=instance_of(str)
    )  # type: str
    concentric = attrib(
        validator=optional(instance_of(int)), default=None
    )  # type: Optional[int]
    radialHour = attrib(
        validator=optional(instance_of(int)), default=None
    )  # type: Optional[int]
    radialMinute = attrib(
        validator=optional(instance_of(int)), default=None
    )  # type: Optional[int]


    def _cmpValue(self) -> Any:
        return (
            self.concentric, self.radialHour, self.radialMinute,
            self.description,
        )


    def _cmp(self, other: Any, methodName: str) -> bool:
        if other.__class__ is self.__class__:
            selfValue = self._cmpValue()
            otherValue = other._cmpValue()
            selfValueCmp = getattr(selfValue, methodName)
            return selfValueCmp(otherValue)

        if other.__class__ is TextOnlyAddress:
            if (
                self.concentric is None and
                self.radialHour is None and
                self.radialMinute is None
            ):
                return getattr(self.description, methodName)(other.description)

        return NotImplemented


    def __hash__(self) -> int:
        if (
            self.concentric is None and
            self.radialHour is None and
            self.radialMinute is None
        ):
            return hash(self.description)

        return hash((
            self.concentric, self.radialHour, self.radialMinute,
            self.description
        ))


    def __eq__(self, other: Any) -> bool:
        return self._cmp(other, "__eq__")


    def __ne__(self, other: Any) -> bool:
        return self._cmp(other, "__ne__")


    def __lt__(self, other: Any) -> bool:
        return self._cmp(other, "__lt__")


    def __le__(self, other: Any) -> bool:
        return self._cmp(other, "__le__")


    def __gt__(self, other: Any) -> bool:
        return self._cmp(other, "__gt__")


    def __ge__(self, other: Any) -> bool:
        return self._cmp(other, "__ge__")
