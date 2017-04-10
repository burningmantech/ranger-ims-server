# -*- test-case-name: ranger-ims-server.ext.test.test_enum -*-
"""
Extensions to :mod:`enum`
"""

from enum import Enum, unique


__all__ = (
    "Enum",
    "enumOrdering",
    "unique",
)



def enumOrdering(enumClass):
    def equal(self, other):
        return self is other

    def notEqual(self, other):
        return self is not other

    def compare(self, other, lessThan):
        if other in enumClass:
            for incidentPriority in enumClass:
                if incidentPriority is self:
                    return lessThan
                elif incidentPriority is other:
                    return not lessThan

        return NotImplemented

    def lessThan(self, other):
        if self is other:
            return False

        return compare(self, other, True)

    def lessThanOrEqual(self, other):
        if self is other:
            return True

        return compare(self, other, True)

    def greaterThan(self, other):
        if self is other:
            return False

        return compare(self, other, False)

    def greaterThanOrEqual(self, other):
        if self is other:
            return True

        return compare(self, other, False)

    enumClass.__eq__ = equal
    enumClass.__ne__ = notEqual
    enumClass.__lt__ = lessThan
    enumClass.__le__ = lessThanOrEqual
    enumClass.__gt__ = greaterThan
    enumClass.__ge__ = greaterThanOrEqual

    return enumClass
