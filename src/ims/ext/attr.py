# -*- test-case-name: ranger-ims-server.ext.test.test_attr -*-
"""
Extensions to :mod:`attr`
"""

from typing import Any, Callable, Iterable, Tuple, TypeVar

from attr import Attribute


__all__ = (
    "Validator",
    "required",
    "sorted_tuple",
    "true",
)


T = TypeVar("T")

Validator = Callable[[Any, Attribute, Any], None]


##
# Validators
##

def required(instance: Any, attribute: Attribute, value: Any) -> None:
    """
    Validate that the given value is not :obj:`None`.
    """
    if value is None:
        raise ValueError(f"{attribute.name!r} may not be None")


def true(validator: Validator) -> Validator:
    """
    Return a validator that checks that its given value is true.
    """
    def true(instance: Any, attribute: Attribute, value: Any) -> None:
        if not value:
            raise ValueError(
                f"{attribute.name!r} must be true, not {value!r}"
            )
        validator(instance, attribute, value)
    return true


##
# Converters
##

def sorted_tuple(iterable: Iterable[T]) -> Tuple[T, ...]:
    """
    Sort and convert an iterable into a tuple.
    """
    return tuple(sorted(iterable))
