"""
Incident
"""

from datetime import datetime as DateTime
from collections.abc import Iterable

from ._location import Location
from ._priority import IncidentPriority
from ._state import IncidentState
from ..ext.attr import attrib, attrs, instanceOf, optional


__all__ = ()



@attrs(frozen=True)
class Incident(object):
    """
    Incident
    """

    number        = attrib(validator=instanceOf(int))
    created       = attrib(validator=instanceOf(DateTime))
    state         = attrib(validator=instanceOf(IncidentState))
    priority      = attrib(validator=instanceOf(IncidentPriority))
    summary       = attrib(validator=optional(instanceOf(str)))
    rangers       = attrib(validator=instanceOf(Iterable))  # FIXME: validator
    incidentTypes = attrib(validator=instanceOf(Iterable))  # FIXME: validator
    location      = attrib(validator=instanceOf(Location))
    reportEntries = attrib(validator=instanceOf(Iterable))  # FIXME: validator
