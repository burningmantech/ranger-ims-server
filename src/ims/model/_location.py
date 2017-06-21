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
Location
"""

from typing import Any, TypeVar

from attr import asdict, attrib, attrs
from attr.validators import instance_of

from ._address import Address


__all__ = ()


TLocation = TypeVar("TLocation", bound="Location")



@attrs(frozen=True)
class Location(Address):
    """
    Location
    """

    name    = attrib(validator=instance_of(str))      # type: str
    address = attrib(validator=instance_of(Address))  # type: Address


    def replace(self: TLocation, **kwargs: Any) -> TLocation:
        """
        Return a new location with the same values, except those specified by
        keyword arguments.
        """
        newArgs = asdict(self, recurse=False)
        newArgs.update(kwargs)
        return self.__class__(**newArgs)
