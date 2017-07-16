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
from typing import Any, TypeVar

from attr import asdict, attrib, attrs
from attr.validators import instance_of

from ims.ext.attr import true


__all__ = ()



TReportEntry = TypeVar("TReportEntry", bound="ReportEntry")


@attrs(frozen=True, cmp=False)
class ReportEntry(object):
    """
    Report entry

    A report entry is text with an associated author and time stamp.
    """

    created: DateTime = attrib(validator=instance_of(DateTime))
    author: str = attrib(validator=true(instance_of(str)))
    automatic: bool = attrib(validator=instance_of(bool))
    text: str = attrib(validator=true(instance_of(str)))


    def __str__(self) -> str:
        if self.automatic:
            automatic = "*"
        else:
            automatic = ""

        return "{} {}{}: {}".format(
            self.created, self.author, automatic, self.text
        )


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


    def replace(self: TReportEntry, **kwargs: Any) -> TReportEntry:
        """
        Return a new report entry with the same values, except those specified
        by keyword arguments.
        """
        newArgs = asdict(self, recurse=False)
        newArgs.update(kwargs)
        return self.__class__(**newArgs)
