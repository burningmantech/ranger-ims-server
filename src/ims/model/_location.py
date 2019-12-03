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

from typing import Optional

from attr import attrib, attrs

from ._address import Address, TextOnlyAddress
from ._replace import ReplaceMixIn

__all__ = ()


def convertAddress(address: Optional[Address]) -> Address:
    if address is None:
        address = TextOnlyAddress(description=None)

    return address


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class Location(Address, ReplaceMixIn):
    """
    Location
    """

    name: Optional[str]
    address: Address = attrib(converter=convertAddress)
