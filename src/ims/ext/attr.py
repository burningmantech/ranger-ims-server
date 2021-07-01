# -*- test-case-name: ranger-ims-server.ext.test.test_attr -*-
"""
Extensions to :mod:`attr`
"""

from typing import Iterable, TypeVar


__all__ = ("sorted_tuple",)


T = TypeVar("T")


##
# Converters
##


def sorted_tuple(iterable: Iterable[T]) -> tuple[T, ...]:
    """
    Sort and convert an iterable into a tuple.
    """
    return tuple(sorted(iterable))  # type: ignore[type-var]
