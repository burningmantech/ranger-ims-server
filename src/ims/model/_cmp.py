# -*- test-case-name: ranger-ims-server.model.test.test_cmp -*-

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
Comparison mix-in
"""

from abc import ABC, abstractmethod
from typing import Any


__all__ = ()



class ComparisonMixIn(ABC):
    """
    Mix-in class with support for comparison operators.
    """

    @abstractmethod
    def _cmpValue(self) -> Any:
        """
        Returns a value for use in comparison methods.
        """


    def _cmp(self, other: Any, methodName: str) -> bool:
        if other.__class__ is self.__class__:
            selfValue = self._cmpValue()
            otherValue = other._cmpValue()
            selfValueCmp = getattr(selfValue, methodName)
            return selfValueCmp(otherValue)
        else:
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
