# -*- test-case-name: ranger-ims-server.ext.test.test_enum -*-
"""
Extensions to :mod:`enum`
"""

from enum import Enum, auto, unique
from typing import Any, Callable, Iterable, List, cast


__all__ = (
    "Enum",
    "Names",
    "auto",
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

        return NotImplemented  # type: ignore[no-any-return]

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

    enumClass.__eq__ = cast(Callable, equal)  # type: ignore[assignment]
    enumClass.__ne__ = cast(Callable, notEqual)  # type: ignore[assignment]
    enumClass.__lt__ = cast(Callable, lessThan)  # type: ignore[operator]
    enumClass.__le__ = cast(Callable, lessThanOrEqual)  # type: ignore[operator]
    enumClass.__gt__ = cast(Callable, greaterThan)  # type: ignore[operator]
    enumClass.__ge__ = cast(  # type: ignore[operator]
        Callable, greaterThanOrEqual
    )

    return enumClass


class Names(Enum):
    """
    Enumerated names.
    """

    @staticmethod
    def _generate_next_value_(
        name: str, start: int, count: int, last_values: List
    ) -> str:
        return name
