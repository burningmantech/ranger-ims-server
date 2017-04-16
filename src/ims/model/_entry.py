"""
Report entry
"""

from datetime import datetime as DateTime
from typing import Any

from ._ranger import Ranger
from ..ext.attr import attrib, attrs, instanceOf, true


__all__ = ()



@attrs(frozen=True, cmp=False)
class ReportEntry(object):
    """
    Report entry

    A report entry is text with an associated author and time stamp.
    """

    created = attrib(validator=instanceOf(DateTime))
    author = attrib(validator=instanceOf(Ranger))
    automatic = attrib(validator=instanceOf(bool))
    text = attrib(validator=true(instanceOf(str)))


    def _cmpKey(self) -> Any:
        return (self.created, self.author, not self.automatic, self.text)


    def _cmp(self, other, methodName):
        if other.__class__ is self.__class__:
            selfKey = self._cmpKey()
            otherKey = other._cmpKey()
            selfKeyCmp = getattr(selfKey, methodName)
            return selfKeyCmp(otherKey)
        else:
            return NotImplemented


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
