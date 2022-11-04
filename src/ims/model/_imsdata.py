# -*- test-case-name: ranger-ims-server.model.test.test_imsdata -*-

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
IMS Data
"""

from collections.abc import Iterable

from attr import attrib
from attrs import frozen

from ._eventdata import EventData
from ._replace import ReplaceMixIn
from ._type import IncidentType


__all__ = ()


def freezeEventDatas(eventDatas: Iterable[EventData]) -> frozenset[EventData]:
    return frozenset(eventDatas)


def freezeIncidentTypes(
    incidentTypes: Iterable[IncidentType],
) -> frozenset[IncidentType]:
    return frozenset(incidentTypes)


@frozen(kw_only=True)
class IMSData(ReplaceMixIn):
    """
    IMS Data container

    Encapsulates all data associated with an IMS service.
    """

    events: frozenset[EventData] = attrib(converter=freezeEventDatas)
    incidentTypes: frozenset[IncidentType] = attrib(
        converter=freezeIncidentTypes
    )
