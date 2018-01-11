# -*- test-case-name: ranger-ims-server.ext.test.test_enum -*-
"""
Extensions to :mod:`enum`
"""

from enum import Enum, unique
from typing import Any, Callable, Iterable, cast


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
    def equal(self: Enum, other: Any) -> bool:
        return self is other

    def notEqual(self: Enum, other: Any) -> bool:
        return self is not other

    def compare(self: Enum, other: Any, lessThan: bool) -> bool:
        if other in cast(Iterable, enumClass):
            for enumInstance in cast(Iterable, enumClass):
                if enumInstance is self:
                    return lessThan
                elif enumInstance is other:
                    return not lessThan

        return NotImplemented

    def lessThan(self: Enum, other: Any) -> bool:
        if self is other:
            return False

        return compare(self, other, True)

    def lessThanOrEqual(self: Enum, other: Any) -> bool:
        if self is other:
            return True

        return compare(self, other, True)

    def greaterThan(self: Enum, other: Any) -> bool:
        if self is other:
            return False

        return compare(self, other, False)

    def greaterThanOrEqual(self: Enum, other: Any) -> bool:
        if self is other:
            return True

        return compare(self, other, False)

    enumClass.__eq__ = cast(Callable, equal)
    enumClass.__ne__ = cast(Callable, notEqual)
    enumClass.__lt__ = cast(Callable, lessThan)
    enumClass.__le__ = cast(Callable, lessThanOrEqual)
    enumClass.__gt__ = cast(Callable, greaterThan)
    enumClass.__ge__ = cast(Callable, greaterThanOrEqual)

    return enumClass
