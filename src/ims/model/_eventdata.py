# -*- test-case-name: ranger-ims-server.model.test.test_eventdata -*-

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
Event Data
"""

from collections.abc import Iterable, Mapping

from attrs import field, mutable

from ims.ext.attr import sorted_tuple
from ims.ext.frozendict import FrozenDict

from ._event import Event
from ._eventaccess import EventAccess
from ._incident import Incident
from ._report import IncidentReport


__all__ = ()


def sortAndFreezeIncidents(incidents: Iterable[Incident]) -> Iterable[Incident]:
    return sorted_tuple(incidents)


def sortAndFreezeIncidentReports(
    incidentReports: Iterable[IncidentReport],
) -> Iterable[IncidentReport]:
    return sorted_tuple(incidentReports)


def freezeConcentricStreets(
    concentricStreets: Mapping[str, str]
) -> Mapping[str, str]:
    return FrozenDict.fromMapping(concentricStreets)


@mutable(kw_only=True)
class EventData:
    """
    Event Data container

    Encapsulates all data associated with an event.
    """

    event: Event
    access: EventAccess
    concentricStreets: Mapping[str, str] = field(
        converter=freezeConcentricStreets
    )
    incidents: Iterable[Incident] = field(converter=sortAndFreezeIncidents)
    incidentReports: Iterable[IncidentReport] = field(
        converter=sortAndFreezeIncidentReports
    )
