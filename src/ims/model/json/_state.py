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
JSON serialization/deserialization for incident state
"""

from enum import Enum, unique
from typing import Type, cast

from ._json import registerDeserializer, registerSerializer
from .._state import IncidentState


__all__ = ()


@unique
class IncidentStateJSONValue(Enum):
    """
    Incident state JSON values
    """

    new = "new"
    onHold = "on_hold"
    dispatched = "dispatched"
    onScene = "on_scene"
    closed = "closed"


def serializeIncidentState(incidentState: IncidentState) -> str:
    constant = cast(
        IncidentStateJSONValue,
        getattr(IncidentStateJSONValue, incidentState.name),
    )
    return cast(str, constant.value)


registerSerializer(IncidentState, serializeIncidentState)


def deserializeIncidentState(
    obj: str, cl: Type[IncidentState]
) -> IncidentState:
    assert cl is IncidentState, (cl, obj)

    return cast(
        IncidentState, getattr(IncidentState, IncidentStateJSONValue(obj).name)
    )


registerDeserializer(IncidentState, deserializeIncidentState)
