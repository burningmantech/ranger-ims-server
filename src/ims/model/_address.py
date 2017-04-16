"""
Address
"""

from ..ext.attr import attrib, attrs, instanceOf


__all__ = ()



class Address(object):
    """
    Location address
    """



@attrs(frozen=True)
class TextOnlyAddress(Address):
    """
    Address

    An address contains a description of a location.
    """

    description = attrib(validator=instanceOf(str))



@attrs(frozen=True)
class RodGarettAddress(Address):
    """
    Rod Garett Address

    Address at concentric and radial streets, as per Rod Garett's design for
    Black Rock City.
    """

    concentric   = attrib(validator=instanceOf(int))
    radialHour   = attrib(validator=instanceOf(int))
    radialMinute = attrib(validator=instanceOf(int))
    description  = attrib(validator=instanceOf(str))
