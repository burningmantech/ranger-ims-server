"""
Incident type
"""

from enum import Enum, unique


__all__ = ()



@unique
class IncidentType(Enum):
    """
    Incident types

    Incident types are a means to categorize incidents.
    Incident types are generally represented as (arbitrary) strings.
    The incident types enumerated here are those that have some relevance to
    the Incident Management System itself, meaning they are treated specially.
    """

    admin = "Admin"
    junk  = "Junk"
