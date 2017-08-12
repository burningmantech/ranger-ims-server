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
JSON serialization/deserialization for Rangers
"""

from enum import Enum, unique
from typing import Any, Dict, List, Optional, Type

from ._json import (
    deserialize, jsonSerialize, registerDeserializer, registerSerializer
)
from .._ranger import Ranger, RangerStatus


__all__ = ()



@unique
class RangerJSONKey(Enum):
    """
    Ranger JSON keys
    """

    handle = "handle"
    name   = "name"
    status = "status"
    email  = "email"
    onSite = "on_site"
    dmsID  = "dms_id"



class RangerJSONType(Enum):
    """
    Ranger attribute types
    """

    handle = str
    name   = str
    status = RangerStatus
    email  = List[str]
    onSite = bool
    dmsID  = Optional[int]



def serializeRanger(ranger: Ranger) -> Dict[str, Any]:
    # Map Ranger attribute names to JSON dict key names
    return dict(
        (key.value, jsonSerialize(getattr(ranger, key.name)))
        for key in RangerJSONKey
    )

registerSerializer(Ranger, serializeRanger)


def deserializeRanger(obj: Dict[str, Any], cl: Type) -> Ranger:
    assert cl is Ranger, (cl, obj)

    return deserialize(
        obj, Ranger,
        RangerJSONType, RangerJSONKey,
    )

registerDeserializer(Ranger, deserializeRanger)



class RangerStatusJSONValue(Enum):
    """
    Ranger status JSON values
    """

    prospective = "prospective"
    alpha       = "alpha"
    bonked      = "bonked"
    active      = "active"
    inactive    = "inactive"
    retired     = "retired"
    uberbonked  = "uberbonked"
    vintage     = "vintage"
    deceased    = "deceased"
    other       = "(unknown)"


def serializeRangerStatus(rangerStatus: RangerStatus) -> str:
    return getattr(RangerStatusJSONValue, rangerStatus.name).value

registerSerializer(RangerStatus, serializeRangerStatus)


def deserializeRangerStatus(obj: int, cl: Type) -> RangerStatus:
    assert cl is RangerStatus, (cl, obj)

    return getattr(RangerStatus, RangerStatusJSONValue(obj).name)

registerDeserializer(RangerStatus, deserializeRangerStatus)
