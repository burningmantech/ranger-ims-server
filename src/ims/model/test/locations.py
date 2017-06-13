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
Test data.
"""

from .._address import RodGarettAddress, TextOnlyAddress
from .._location import Location


__all__ = ()



theMan = Location(
    name="The Man",
    address=TextOnlyAddress(description="The Man"),
)

hq = Location(
    name="Ranger Headquarters",
    address=RodGarettAddress(
        concentric="0", radialHour=5, radialMinute=45,
        description="Ranger Headquarters",
    ),
)

berlin = Location(
    name="Ranger Outpost Berlin",
    address=RodGarettAddress(
        concentric="3", radialHour=3, radialMinute=0,
        description="Ranger Outpost",
    ),
)

tokyo = Location(
    name="Ranger Outpost Tokyo",
    address=RodGarettAddress(
        concentric="3", radialHour=9, radialMinute=0,
        description="Ranger Outpost",
    ),
)

geneva = Location(
    name="Ranger Camp Geneva",
    address=RodGarettAddress(
        concentric="10", radialHour=7, radialMinute=30,
        description="Ranger Camp",
    ),
)

moscow = Location(
    name="Ranger Camp Moscow",
    address=RodGarettAddress(
        concentric="3", radialHour=5, radialMinute=30,
        description="Ranger Camp",
    ),
)
