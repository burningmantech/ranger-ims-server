# -*- test-case-name: ranger-ims-server.model.test.test_entry -*-

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
Report entry
"""

from datetime import datetime as DateTime
from typing import Any

from attr import attrib, attrs
from attr.validators import instance_of

from ims.ext.attr import true


__all__ = ()



@attrs(frozen=True, cmp=False)
class ReportEntry(object):
    """
    Report entry

    A report entry is text with an associated author and time stamp.
    """

    created   = attrib(validator=instance_of(DateTime))   # type: DateTime
    author    = attrib(validator=true(instance_of(str)))  # type: str
    automatic = attrib(validator=instance_of(bool))       # type: bool
    text      = attrib(validator=true(instance_of(str)))  # type: str


    def _cmpValue(self) -> Any:
        return (self.created, self.author, not self.automatic, self.text)


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
