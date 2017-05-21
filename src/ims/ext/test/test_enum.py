"""
Tests for :mod:`ranger-ims-server.ext.enum`
"""

from ..enum import Enum, enumOrdering
from ..trial import TestCase


__all__ = ()



@enumOrdering
class Thing(Enum):
    """
    Enumeration of some things.
    """

    first  = object()
    second = object()
    third  = object()



class EnumOrderingTests(TestCase):
    """
    Tests for :func:`enumOrdering`.
    """

    def test_equal(self) -> None:
        """
        :func:`enumOrdering` sets ``__eq__``.
        """
        self.assertFalse(Thing.first.__eq__(Thing.second))
        self.assertFalse(Thing.second.__eq__(Thing.first))

        self.assertTrue(Thing.second.__eq__(Thing.second))

        self.assertFalse(Thing.second.__eq__(Thing.third))
        self.assertFalse(Thing.third.__eq__(Thing.second))

        self.assertFalse(Thing.second.__eq__(self))


    def test_notEqual(self) -> None:
        """
        :func:`enumOrdering` sets ``__ne__``.
        """
        self.assertTrue(Thing.first.__ne__(Thing.second))
        self.assertTrue(Thing.second.__ne__(Thing.first))

        self.assertFalse(Thing.second.__ne__(Thing.second))

        self.assertTrue(Thing.second.__ne__(Thing.third))
        self.assertTrue(Thing.third.__ne__(Thing.second))

        self.assertTrue(Thing.second.__ne__(self))


    def test_lessThan(self) -> None:
        """
        :func:`enumOrdering` sets ``__lt__``.
        """
        self.assertTrue(Thing.first.__lt__(Thing.second))
        self.assertFalse(Thing.second.__lt__(Thing.first))

        self.assertFalse(Thing.second.__lt__(Thing.second))

        self.assertTrue(Thing.second.__lt__(Thing.third))
        self.assertFalse(Thing.third.__lt__(Thing.second))

        self.assertIdentical(Thing.second.__lt__(self), NotImplemented)


    def test_lessThanOrEqual(self) -> None:
        """
        :func:`enumOrdering` sets ``__le__``.
        """
        self.assertTrue(Thing.first.__le__(Thing.second))
        self.assertFalse(Thing.second.__le__(Thing.first))

        self.assertTrue(Thing.second.__le__(Thing.second))

        self.assertTrue(Thing.second.__le__(Thing.third))
        self.assertFalse(Thing.third.__le__(Thing.second))

        self.assertIdentical(Thing.second.__le__(self), NotImplemented)


    def test_greaterThan(self) -> None:
        """
        :func:`enumOrdering` sets ``__gt__``.
        """
        self.assertFalse(Thing.first.__gt__(Thing.second))
        self.assertTrue(Thing.second.__gt__(Thing.first))

        self.assertFalse(Thing.second.__gt__(Thing.second))

        self.assertFalse(Thing.second.__gt__(Thing.third))
        self.assertTrue(Thing.third.__gt__(Thing.second))

        self.assertIdentical(Thing.second.__gt__(self), NotImplemented)


    def test_greaterThanOrEqual(self) -> None:
        """
        :func:`enumOrdering` sets ``__ge__``.
        """
        self.assertFalse(Thing.first.__ge__(Thing.second))
        self.assertTrue(Thing.second.__ge__(Thing.first))

        self.assertTrue(Thing.second.__ge__(Thing.second))

        self.assertFalse(Thing.second.__ge__(Thing.third))
        self.assertTrue(Thing.third.__ge__(Thing.second))

        self.assertIdentical(Thing.second.__ge__(self), NotImplemented)
