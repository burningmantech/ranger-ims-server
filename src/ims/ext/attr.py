# -*- test-case-name: ranger-ims-server.ext.test.test_attr -*-
"""
Extensions to :mod:`attr`
"""

from collections.abc import Iterable


__all__ = ("sorted_tuple",)


##
# Converters
##


def sorted_tuple[T](iterable: Iterable[T]) -> tuple[T, ...]:
    """
    Sort and convert an iterable into a tuple.
    """
    return tuple(sorted(iterable))  # type: ignore[type-var]
