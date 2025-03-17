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
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import frozen

from ._cmp import ComparisonMixIn
from ._replace import ReplaceMixIn


if TYPE_CHECKING:
    from collections.abc import Callable


__all__ = ()


TRodGarettAddress = TypeVar("TRodGarettAddress", bound="RodGarettAddress")


@frozen(kw_only=True, eq=False)
class Address(ABC):  # noqa: B024
    """
    Location address
    """

    description: str | None = None


@frozen(kw_only=True, eq=False)
class TextOnlyAddress(Address, ComparisonMixIn):
    """
    Address

    An address contains a description of a location.
    """

    description: str | None = None

    def _cmpValue(self) -> Any:
        return self.description

    def _cmp(self, other: Any, methodName: str) -> bool:
        if other is None:
            return self.description is None

        return ComparisonMixIn._cmp(self, other, methodName)


@frozen(kw_only=True, eq=False)
class RodGarettAddress(Address, ComparisonMixIn, ReplaceMixIn):
    """
    Rod Garett Address

    Address at concentric and radial streets, as per Rod Garett's design for
    Black Rock City.
    """

    description: str | None = None
    concentric: str | None = None
    radialHour: int | None = None
    radialMinute: int | None = None

    def _allNone(self) -> bool:
        return (
            self.concentric is None
            and self.radialHour is None
            and self.radialMinute is None
        )

    def _cmpValue(self) -> Any:
        return (
            self.concentric,
            self.radialHour,
            self.radialMinute,
            self.description,
        )

    def _cmp(self, other: Any, methodName: str) -> bool:
        if other is None:
            return self._allNone()

        if other.__class__ is TextOnlyAddress and self._allNone():
            method = cast(
                "Callable[[str], bool]", getattr(self.description, methodName)
            )
            return method(other.description)

        return ComparisonMixIn._cmp(self, other, methodName)

    def __hash__(self) -> int:
        if self._allNone():
            return hash(self.description)

        return ComparisonMixIn.__hash__(self)
