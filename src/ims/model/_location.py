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


from attrs import field, mutable

from ._address import Address, TextOnlyAddress
from ._replace import ReplaceMixIn


__all__ = ()


def convertAddress(address: Address | None) -> Address:
    if address is None:
        address = TextOnlyAddress(description=None)

    return address


@mutable(kw_only=True)
class Location(Address, ReplaceMixIn):
    """
    Location
    """

    name: str | None
    address: Address = field(converter=convertAddress)
