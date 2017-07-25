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
JSON serialization/deserialization for report entries
"""

from datetime import datetime as DateTime
from enum import Enum, unique
from typing import Any, Dict, Type

from ._json import (
    jsonDeserialize, jsonSerialize, registerDeserializer, registerSerializer
)
from .._entry import ReportEntry


__all__ = ()



@unique
class ReportEntryJSONKey(Enum):
    """
    Incident state JSON keys
    """

    created   = "created"
    author    = "author"
    automatic = "system_entry"
    text      = "text"



class ReportEntryJSONType(Enum):
    """
    Incident state JSON keys
    """

    created   = DateTime
    author    = str
    automatic = bool
    text      = str



def serializeReportEntry(reportEntry: ReportEntry) -> Dict[str, Any]:
    # Map ReportEntry attribute names to JSON dict key names
    return dict(
        (key.value, jsonSerialize(getattr(reportEntry, key.name)))
        for key in ReportEntryJSONKey
    )


registerSerializer(ReportEntry, serializeReportEntry)


def deserializeReportEntry(obj: Dict[str, Any], cl: Type) -> ReportEntry:
    assert cl is ReportEntry, (cl, obj)

    return ReportEntry(
        # Map JSON dict key names to ReportEntry attribute names
        **dict(
            (
                key.name,
                jsonDeserialize(
                    obj[key.value],
                    getattr(ReportEntryJSONType, key.name).value
                )
            )
            for key in ReportEntryJSONKey
        )
    )


registerDeserializer(ReportEntry, deserializeReportEntry)
