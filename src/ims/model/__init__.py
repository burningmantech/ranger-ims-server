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
Incident Management System data model
"""

from ._address import Address, RodGarettAddress, TextOnlyAddress
from ._entry import ReportEntry
from ._event import Event
from ._eventaccess import EventAccess
from ._eventdata import EventData
from ._imsdata import IMSData
from ._incident import Incident
from ._location import Location
from ._priority import IncidentPriority
from ._ranger import Ranger, RangerStatus
from ._report import IncidentReport
from ._state import IncidentState
from ._type import IncidentType, KnownIncidentType


__all__ = (
    "Address",
    "Event",
    "EventAccess",
    "EventData",
    "IMSData",
    "Incident",
    "IncidentPriority",
    "IncidentReport",
    "IncidentState",
    "IncidentType",
    "KnownIncidentType",
    "Location",
    "Ranger",
    "RangerStatus",
    "ReportEntry",
    "RodGarettAddress",
    "TextOnlyAddress",
)
