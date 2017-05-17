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
JSON serialization/deserialization for incident priority
"""

from enum import Enum
from typing import Type

from ._json import registerDeserializer, registerSerializer
from .._priority import IncidentPriority


__all__ = ()



class IncidentPriorityJSON(Enum):
    """
    Incident priority JSON values
    """

    high   = 1
    normal = 3
    low    = 5



def serializeIncidentPriority(incidentPriority: IncidentPriority) -> str:
    return getattr(IncidentPriorityJSON, incidentPriority.name).value


registerSerializer(IncidentPriority, serializeIncidentPriority)


def deserializeIncidentPriority(cl: Type, obj: int) -> IncidentPriority:
    assert cl is IncidentPriority, (cl, obj)

    return getattr(IncidentPriority, IncidentPriorityJSON(obj).name)


registerDeserializer(IncidentPriority, deserializeIncidentPriority)
