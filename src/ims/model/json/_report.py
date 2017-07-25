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
from typing import Any, Dict, List, Optional, Type

from ._json import (
    jsonDeserialize, jsonSerialize, registerDeserializer, registerSerializer
)
from .._entry import ReportEntry
from .._report import IncidentReport


__all__ = ()



@unique
class IncidentReportJSONKey(Enum):
    """
    Incident report JSON keys
    """

    number        = "number"
    created       = "created"
    summary       = "summary"
    reportEntries = "report_entries"



class IncidentReportJSONType(Enum):
    """
    Incident report attribute types
    """

    number        = int
    created       = DateTime
    summary       = Optional[str]
    reportEntries = List[ReportEntry]



def serializeIncidentReport(incidentReport: IncidentReport) -> Dict[str, Any]:
    # Map IncidentReport attribute names to JSON dict key names
    return dict(
        (key.value, jsonSerialize(getattr(incidentReport, key.name)))
        for key in IncidentReportJSONKey
    )


registerSerializer(IncidentReport, serializeIncidentReport)


def deserializeIncidentReport(obj: Dict[str, Any], cl: Type) -> IncidentReport:
    assert cl is IncidentReport, (cl, obj)

    return IncidentReport(
        # Map JSON dict key names to IncidentReport attribute names
        **dict(
            (
                key.name,
                jsonDeserialize(
                    obj[key.value],
                    getattr(IncidentReportJSONType, key.name).value
                )
            )
            for key in IncidentReportJSONKey
        )
    )


registerDeserializer(IncidentReport, deserializeIncidentReport)
