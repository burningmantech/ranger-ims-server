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
JSON serialization/deserialization for access validity
"""

from enum import Enum, unique
from typing import cast

from .._accessvalidity import AccessValidity
from ._json import registerDeserializer, registerSerializer


__all__ = ()


@unique
class AccessValidityJSONValue(Enum):
    """
    Access validity JSON values
    """

    always = "always"
    onsite = "onsite"


def serializeAccessValidity(accessValidity: AccessValidity) -> str:
    constant = cast(
        "AccessValidityJSONValue",
        getattr(AccessValidityJSONValue, accessValidity.name),
    )
    return constant.value


registerSerializer(AccessValidity, serializeAccessValidity)


def deserializeAccessValidity(obj: str, cl: type[AccessValidity]) -> AccessValidity:
    assert cl is AccessValidity, (cl, obj)

    return cast(
        "AccessValidity", getattr(AccessValidity, AccessValidityJSONValue(obj).name)
    )


registerDeserializer(AccessValidity, deserializeAccessValidity)
