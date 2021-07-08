# -*- test-case-name: ranger-ims-server.model.test.test_convert -*-

##
# See the file COPYRIGHT for copyright information.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
##

"""
Converters
"""

from datetime import datetime as DateTime
from typing import Iterable


__all__ = ()


def freezeIntegers(integers: Iterable[int]) -> frozenset[int]:
    return frozenset(integers)


def freezeStrings(strings: Iterable[str]) -> frozenset[str]:
    return frozenset(strings)


def normalizeDateTime(dateTime: DateTime) -> DateTime:
    """
    Shave some precision off of DateTimes, since it may not round-trip well
    into all data stores with full precision and we don't need that kind of
    precision.
    """
    microsecond = int(round(dateTime.microsecond, -4))
    if microsecond == 1000000:  # Rounded up a wee bit too far
        microsecond = 990000
    return dateTime.replace(microsecond=microsecond)
