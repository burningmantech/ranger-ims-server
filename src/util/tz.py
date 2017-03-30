# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Time zone utilities.
"""

from datetime import datetime as DateTime, timezone as TimeZone


__all__ = (
    "utcNow",
)



def utcNow():
    """
    Compute current time in UTC timezone.
    """
    return DateTime.utcnow().replace(tzinfo=TimeZone.utc)
