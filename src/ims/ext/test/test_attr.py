"""
Tests for :mod:`ranger-ims-server.ext.attr`
"""

from attr import attrib, attrs, instance_of

from ..attr import required, true
from ..trial import TestCase


__all__ = ()



@attrs
class NamedClass(object):
    """
    Class for testing :func:`required` validator.
    """

    name = attrib(validator=required)  # type: str



@attrs
class MustBeNiceClass(object):
    """
    Class for testing :func:`true` validator.
    """

    nice = attrib(validator=true(instance_of(str)))  # type: str



class ValidatorTests(TestCase):
    """
    Tests for :mod:`config_service.util.validators`
    """

    def test_required_value(self) -> None:
        """
        :func:`required` does not raise :exc:`ValueError` if given a value that
        is not :obj:`None`.
        """
        try:
            NamedClass(name="foo")
        except ValueError as e:
            self.fail(e)


    def test_required_none(self) -> None:
        """
        :func:`required` raises :exc:`ValueError` if given a value that is
        :obj:`None`.
        """
        self.assertRaises(ValueError, NamedClass, name=None)


    def test_true_true(self) -> None:
        """
        :func:`true` does not raise :exc:`ValueError` if given a value that is
        true.
        """
        try:
            MustBeNiceClass(nice="Hello!")
        except ValueError as e:
            self.fail(e)


    def test_true_false(self) -> None:
        """
        :func:`required` raises :exc:`ValueError` if given a value that is
        false.
        """
        self.assertRaises(ValueError, MustBeNiceClass, nice="")
