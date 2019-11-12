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
from typing import (
    Any, Callable, Dict, Iterable, List, Mapping, Type, Union, cast
)

from cattr import Converter

from twisted.logger import Logger

from ims.ext.frozendict import FrozenDict
from ims.ext.json import dateTimeAsRFC3339Text, rfc3339TextAsDateTime


__all__ = ()


log = Logger()


JSON = Union[Mapping[str, Any], Iterable, int, str, float, bool, None]



class JSONCodecError(Exception):
    """
    Error while serializing or deserializing JSON data.
    """



converter = Converter()
jsonSerialize = converter.unstructure  # type: Callable[[Any], JSON]
jsonDeserialize = converter.structure

registerSerializer = converter.register_unstructure_hook
registerDeserializer = converter.register_structure_hook


# DateTime

registerSerializer(DateTime, dateTimeAsRFC3339Text)

def deserializeDateTime(obj: str, cl: Type) -> DateTime:
    assert cl is DateTime, (cl, obj)

    return rfc3339TextAsDateTime(obj)

registerDeserializer(DateTime, deserializeDateTime)


# Tuples and sets should serialize like lists

def serializeIterable(iterable: Iterable) -> List:
    return [jsonSerialize(item) for item in iterable]

registerSerializer(frozenset, serializeIterable)
registerSerializer(set, serializeIterable)
registerSerializer(tuple, serializeIterable)


# FrozenDict

def serializeFrozenDict(frozenDict: FrozenDict) -> Any:
    return jsonSerialize(dict(frozenDict))

registerSerializer(FrozenDict, serializeFrozenDict)

def deserializeFrozenDict(obj: Dict, cl: Type) -> FrozenDict:
    assert cl is FrozenDict, (cl, obj)

    return FrozenDict.fromMapping(obj)



# Public API

def jsonObjectFromModelObject(model: Any) -> JSON:
    return jsonSerialize(model)


def modelObjectFromJSONObject(json: JSON, modelClass: type) -> Any:
    try:
        return jsonDeserialize(json, modelClass)
    except KeyError:
        raise JSONCodecError(f"Invalid JSON for {modelClass.__name__}: {json}")


# Utilities

def deserialize(
    obj: Dict[str, Any], cls: Type, typeEnum: Type, keyEnum: Type
) -> Any:
    def deserializeKey(key: Enum) -> Any:
        try:
            cls = getattr(typeEnum, key.name).value
        except AttributeError:
            raise AttributeError(
                "No attribute {attribute!r} in type enum {enum!r}".format(
                    attribute=key.name, enum=typeEnum
                )
            )
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
