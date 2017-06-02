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
Address
"""

from abc import ABC

from attr import attrib, attrs
from attr.validators import instance_of


__all__ = ()



class Address(ABC):
    """
    Location address
    """



@attrs(frozen=True)
class TextOnlyAddress(Address):
    """
    Address

    An address contains a description of a location.
    """

    description = attrib(validator=instance_of(str))  # type: str



@attrs(frozen=True)
class RodGarettAddress(Address):
    """
    Rod Garett Address

    Address at concentric and radial streets, as per Rod Garett's design for
    Black Rock City.
    """

    concentric   = attrib(validator=instance_of(int))  # type: int
    radialHour   = attrib(validator=instance_of(int))  # type: int
    radialMinute = attrib(validator=instance_of(int))  # type: int
    description  = attrib(validator=instance_of(str))  # type: str
