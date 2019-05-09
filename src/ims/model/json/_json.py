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
from enum import Enum
from typing import Any, Dict, Iterable, Type, cast

from cattr import Converter

from twisted.logger import Logger

from ims.ext.json import dateTimeAsRFC3339Text, rfc3339TextAsDateTime


__all__ = ()


log = Logger()



class JSONCodecError(Exception):
    """
    Error while serializing or deserializing JSON data.
    """



converter = Converter()
jsonSerialize = converter.unstructure
jsonDeserialize = converter.structure

registerSerializer = converter.register_unstructure_hook
registerDeserializer = converter.register_structure_hook


# Serialization hooks

registerSerializer(DateTime, dateTimeAsRFC3339Text)


# Deserialization hooks

def deserializeDateTime(obj: str, cl: Type) -> DateTime:
    assert cl is DateTime, (cl, obj)

    return rfc3339TextAsDateTime(obj)


registerDeserializer(DateTime, deserializeDateTime)


def jsonObjectFromModelObject(model: Any) -> Any:
    return jsonSerialize(model)


def modelObjectFromJSONObject(json: Any, modelClass: type) -> Any:
    try:
        return jsonDeserialize(json, modelClass)
    except KeyError:
        raise JSONCodecError(f"Invalid JSON for {modelClass.__name__}: {json}")


# Utilities

def deserialize(
    obj: Dict[str, Any], cls: Type, typeEnum: Type, keyEnum: Type
) -> Any:
    def deserializeKey(key: Enum) -> Any:
        cls = getattr(typeEnum, key.name).value
        try:
            return jsonDeserialize(
                obj.get(key.value, None), cls
            )
        except Exception:
            log.error(
                "Unable to deserialize {key} as {cls} from {json}",
                key=key, cls=cls, json=obj
            )
            raise

    return cls(
        # Map JSON dict key names to RodGarettAddress attribute names
        **{key.name: deserializeKey(key) for key in cast(Iterable, keyEnum)}
    )
