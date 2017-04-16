"""
Location
"""

from ._address import Address
from ..ext.attr import attrib, attrs, instanceOf


__all__ = ()



@attrs(frozen=True)
class Location(Address):
    """
    Location
    """

    name    = attrib(validator=instanceOf(str))
    address = attrib(validator=instanceOf(Address))
