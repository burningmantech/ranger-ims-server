"""
Ranger
"""

from collections.abc import Iterable
from enum import Enum, unique

from ..ext.attr import attrib, attrs, instanceOf, optional, true


__all__ = ()



@unique
class RangerStatus(Enum):
    """
    Ranger status

    A Ranger status denotes the status of a Ranger in the Ranger department.
    """

    prospective = 0
    alpha       = 1
    bonked      = 2
    active      = 3
    inactive    = 4
    retired     = 5
    uberbonked  = 6
    vintage     = 7
    deceased    = 8

    other = -1



@attrs(frozen=True)
class Ranger(object):
    """
    Ranger

    An Ranger contains information about a Black Rock Ranger; a person record
    specific to a Black Rock Ranger.
    """

    handle   = attrib(validator=true(instanceOf(str)))
    name     = attrib(validator=true(instanceOf(str)))
    status   = attrib(validator=instanceOf(RangerStatus))
    email    = attrib(validator=instanceOf(Iterable))  # FIXME: validator
    onSite   = attrib(validator=instanceOf(bool))
    dmsID    = attrib(validator=optional(instanceOf(int)))
    password = attrib(validator=optional(instanceOf(str)))
