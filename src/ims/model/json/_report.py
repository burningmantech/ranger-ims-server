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
JSON serialization/deserialization for field reports
"""

from datetime import datetime as DateTime
from enum import Enum, unique
from typing import Any, Optional, cast

from .._entry import ReportEntry
from .._report import FieldReport
from ._json import (
    deserialize,
    jsonSerialize,
    registerDeserializer,
    registerSerializer,
)


__all__ = ()


@unique
class FieldReportJSONKey(Enum):
    """
    Field report JSON keys
    """

    eventID = "event"
    number = "number"
    created = "created"
    summary = "summary"
    incidentNumber = "incident"
    reportEntries = "report_entries"


class FieldReportJSONType(Enum):
    """
    Field report attribute types
    """

    eventID = str
    number = int
    created = DateTime
    summary = Optional[str]
    incidentNumber = Optional[int]
    reportEntries = list[ReportEntry]


def serializeFieldReport(fieldReport: FieldReport) -> dict[str, Any]:
    # Map FieldReport attribute names to JSON dict key names
    return {
        key.value: jsonSerialize(getattr(fieldReport, key.name))
        for key in FieldReportJSONKey
    }


registerSerializer(FieldReport, serializeFieldReport)


def deserializeFieldReport(obj: dict[str, Any], cl: type[FieldReport]) -> FieldReport:
    assert cl is FieldReport, (cl, obj)

    return cast(
        FieldReport,
        deserialize(
            obj,
            FieldReport,
            FieldReportJSONType,
            FieldReportJSONKey,
        ),
    )


registerDeserializer(FieldReport, deserializeFieldReport)
