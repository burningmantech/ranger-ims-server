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
JSON serialization/deserialization for incident reports
"""

from datetime import datetime as DateTime
from enum import Enum, unique
from typing import Any, Optional, cast

from .._entry import ReportEntry
from .._report import IncidentReport
from ._json import (
    deserialize,
    jsonSerialize,
    registerDeserializer,
    registerSerializer,
)


__all__ = ()


@unique
class IncidentReportJSONKey(Enum):
    """
    Incident report JSON keys
    """

    eventID = "event"
    number = "number"
    created = "created"
    summary = "summary"
    incidentNumber = "incident"
    reportEntries = "report_entries"


class IncidentReportJSONType(Enum):
    """
    Incident report attribute types
    """

    eventID = str
    number = int
    created = DateTime
    summary = Optional[str]
    incidentNumber = Optional[int]
    reportEntries = list[ReportEntry]


def serializeIncidentReport(incidentReport: IncidentReport) -> dict[str, Any]:
    # Map IncidentReport attribute names to JSON dict key names
    return {
        key.value: jsonSerialize(getattr(incidentReport, key.name))
        for key in IncidentReportJSONKey
    }


registerSerializer(IncidentReport, serializeIncidentReport)


def deserializeIncidentReport(
    obj: dict[str, Any], cl: type[IncidentReport]
) -> IncidentReport:
    assert cl is IncidentReport, (cl, obj)

    return cast(
        IncidentReport,
        deserialize(
            obj,
            IncidentReport,
            IncidentReportJSONType,
            IncidentReportJSONKey,
        ),
    )


registerDeserializer(IncidentReport, deserializeIncidentReport)
