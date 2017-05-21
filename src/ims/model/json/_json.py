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
Incident Management System data model JSON serialization/deserialization
"""

from datetime import datetime as DateTime
from typing import Any, Type

from cattr import Converter

from ...ext.json import (
    dateTimeAsRFC3339Text, jsonTextFromObject, rfc3339TextAsDateTime
)


__all__ = ()


converter = Converter()
jsonSerialize = converter.dumps
jsonDeserialize = converter.loads

registerSerializer = converter.register_dumps_hook
registerDeserializer = converter.register_loads_hook


# Serialization hooks

registerSerializer(DateTime, dateTimeAsRFC3339Text)


# Deserialization hooks

def deserializeDateTime(cl: Type, obj: str) -> DateTime:
    assert cl is DateTime, (cl, obj)

    return rfc3339TextAsDateTime(obj)


registerDeserializer(DateTime, deserializeDateTime)


def jsonTextFromModelObject(
    object: Any, pretty: bool = False
) -> str:
    return jsonTextFromObject(jsonSerialize(object), pretty=pretty)
