"""
Event
"""

from ..ext.attr import attrib, attrs, instanceOf, true


__all__ = ()



@attrs(frozen=True)
class Event(object):
    """
    Event

    An event is a container for incident data with an ID.
    """

    id = attrib(validator=true(instanceOf(str)))
