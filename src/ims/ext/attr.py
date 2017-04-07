# -*- test-case-name: ranger-ims-server.ext.test.test_attr -*-
"""
Extensions to :mod:`attr`
"""

from typing import Any, Callable

from attr import Attribute, attrib, attrs
from attr.validators import instance_of as instanceOf, optional, provides


__all__ = (
    "Validator",
    "attrib",
    "attrs",
    "instanceOf",
    "optional",
    "provides",
    "required",
    "true",
)


Validator = Callable[[Any, Attribute, Any], None]


def required(instance: Any, attribute: Attribute, value: Any) -> None:
    """
    Validate that the given value is not :obj:`None`.
    """
    if value is None:
        raise ValueError("{!r} may not be None".format(attribute.name))


def true(validator: Validator) -> Validator:
    """
    Return a validator that checks that its given value is true.
    """
    def true(instance: Any, attribute: Attribute, value: Any) -> None:
        if not value:
            raise ValueError(
                "{!r} must be true, not {!r}".format(attribute.name, value)
            )
        validator(instance, attribute, value)
    return true
