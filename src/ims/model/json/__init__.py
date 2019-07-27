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

from . import _event
from . import _ranger
from . import _type
from ._address import RodGarettAddressJSONKey, TextOnlyAddressJSONKey
from ._entry import ReportEntryJSONKey
from ._eventaccess import EventAccessJSONKey
from ._incident import IncidentJSONKey
from ._json import (
    JSONCodecError, jsonObjectFromModelObject, modelObjectFromJSONObject
)
from ._location import LocationJSONKey
from ._priority import IncidentPriorityJSONValue
from ._report import IncidentReportJSONKey
from ._state import IncidentStateJSONValue

# These were imported only to register the serializers/de-serializers
del _event
del _ranger
del _type


__all__ = (
    "EventAccessJSONKey",
    "IncidentJSONKey",
    "IncidentPriorityJSONValue",
    "IncidentReportJSONKey",
    "IncidentStateJSONValue",
    "JSONCodecError",
    "LocationJSONKey",
    "ReportEntryJSONKey",
    "RodGarettAddressJSONKey",
    "TextOnlyAddressJSONKey",
    "jsonObjectFromModelObject",
    "modelObjectFromJSONObject",
)
