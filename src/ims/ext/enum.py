# -*- test-case-name: ranger-ims-server.ext.test.test_enum -*-
"""
Extensions to :mod:`enum`
"""

from collections.abc import Callable
from enum import Enum, auto, unique
from typing import Any, cast


__all__ = (
    "Enum",
    "Names",
    "auto",
    "enumOrdering",
    "unique",
)


# FIXME: import EnumMeta from somewhere
EnumMeta = type


Comparator = Callable[[object, object], bool]


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
        members: tuple[Enum, ...] = tuple(enumClass)  # type: ignore[arg-type]
        if other in members:
            for member in members:
                if member is self:
                    return lessThan
                elif member is other:
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

    enumClass.__eq__ = cast(Comparator, equal)  # type: ignore[assignment]
    enumClass.__ne__ = cast(Comparator, notEqual)  # type: ignore[assignment]
    enumClass.__lt__ = cast(Comparator, lessThan)  # type: ignore[operator]
    enumClass.__le__ = cast(  # type: ignore[operator]
        Comparator, lessThanOrEqual
    )
    enumClass.__gt__ = cast(Comparator, greaterThan)  # type: ignore[operator]
    enumClass.__ge__ = cast(  # type: ignore[operator]
        Comparator, greaterThanOrEqual
    )

    return enumClass


class Names(Enum):
    """
    Enumerated names.
    """

    @staticmethod
    def _generate_next_value_(
        name: str, start: int, count: int, last_values: list[object]
    ) -> str:
        return name
