"""
Incident priority
"""

from ..ext.enum import Enum, enumOrdering, unique


__all__ = ()



@enumOrdering
@unique
class IncidentPriority(Enum):
    """
    Incident priorities

    Priorities are used to denote the relative urgency of resolving a
    particular incident.
    """

    high   = object()
    normal = object()
    low    = object()
