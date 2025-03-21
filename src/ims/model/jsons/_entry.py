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
from typing import Any, cast

from .._entry import ReportEntry
from ._json import (
    deserialize,
    jsonSerialize,
    registerDeserializer,
    registerSerializer,
)


__all__ = ()


@unique
class ReportEntryJSONKey(Enum):
    """
    Incident state JSON keys
    """

    id = "id"
    created = "created"
    author = "author"
    automatic = "system_entry"
    text = "text"
    stricken = "stricken"
    # this field is added separately below
    # has_attachment = "has_attachment"


class ReportEntryJSONType(Enum):
    """
    Incident state JSON keys
    """

    id = int
    created = DateTime
    author = str
    automatic = bool
    text = str
    stricken = bool
    # has_attachment = bool


def serializeReportEntry(reportEntry: ReportEntry) -> dict[str, Any]:
    # Map ReportEntry attribute names to JSON dict key names
    jsonified = {
        key.value: jsonSerialize(getattr(reportEntry, key.name))
        for key in ReportEntryJSONKey
    }
    # don't add the name of the file itself, as that's secret
    jsonified["has_attachment"] = bool(reportEntry.attachedFile)
    return jsonified


registerSerializer(ReportEntry, serializeReportEntry)


def deserializeReportEntry(obj: dict[str, Any], cl: type[ReportEntry]) -> ReportEntry:
    assert cl is ReportEntry, (cl, obj)

    return cast(
        "ReportEntry",
        deserialize(obj, ReportEntry, ReportEntryJSONType, ReportEntryJSONKey),
    )


registerDeserializer(ReportEntry, deserializeReportEntry)
