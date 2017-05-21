# -*- test-case-name: ranger-ims-server.ext.test.test_enum -*-
"""
Extensions to :mod:`enum`
"""

from enum import Enum, unique
from typing import Any, Iterable, cast


__all__ = (
    "Enum",
    "enumOrdering",
    "unique",
)


# FIXME: import EnumMeta from somewhere
EnumMeta = type


def enumOrdering(enumClass: EnumMeta) -> EnumMeta:
    """
    Decorate an `Enum` class to add comparison methods that order instances in
    the order that they were enumerated.
    """
    enumClass = cast(Iterable, enumClass)

    def equal(self, other: Any) -> bool:
        return self is other

    def notEqual(self, other: Any) -> bool:
        return self is not other

    def compare(self, other: Any, lessThan: bool) -> bool:
        if other in enumClass:
            for incidentPriority in enumClass:
                if incidentPriority is self:
                    return lessThan
                elif incidentPriority is other:
                    return not lessThan

        return NotImplemented

    def lessThan(self, other: Any) -> bool:
        if self is other:
            return False

        return compare(self, other, True)

    def lessThanOrEqual(self, other: Any) -> bool:
        if self is other:
            return True

        return compare(self, other, True)

    def greaterThan(self, other: Any) -> bool:
        if self is other:
            return False

        return compare(self, other, False)

    def greaterThanOrEqual(self, other: Any) -> bool:
        if self is other:
            return True

        return compare(self, other, False)

    enumClass.__eq__ = equal
    enumClass.__ne__ = notEqual
    enumClass.__lt__ = lessThan
    enumClass.__le__ = lessThanOrEqual
    enumClass.__gt__ = greaterThan
    enumClass.__ge__ = greaterThanOrEqual

    return enumClass
