"""
Incident Management System data model
"""

from ._event import Event
from ._priority import IncidentPriority
from ._state import IncidentState
from ._type import IncidentType


__all__ = (
    "Event",
    "IncidentType",
)
