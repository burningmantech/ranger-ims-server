"""
Tests for :mod:`ranger-ims-server.model._event`
"""

from twisted.python.compat import cmp

from .._event import Event
from ...ext.trial import TestCase


__all__ = ()



class EventTests(TestCase):
    """
    Tests for :class:`Event`
    """

    def test_ordering(self) -> None:
        """
        Event ordering corresponds to event ID ordering.
        """
        for idA, idB in (("a", "b"), ("b", "a")):
            eventA = Event(id=idA)
            eventB = Event(id=idB)

            self.assertEqual(cmp(idA, idB), cmp(eventA, eventB))
