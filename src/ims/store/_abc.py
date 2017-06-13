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
Incident Management System data store abstract base classes.
"""

from abc import ABC, abstractmethod
from typing import Iterable

from ims.model import Event, Incident, Ranger


__all__ = ()



class IMSDataStore(ABC):
    """
    Incident Management System data store abstract base class.
    """

    @abstractmethod
    async def events(self) -> Iterable[Event]:
        """
        Look up all events in this store.
        """


    @abstractmethod
    async def createEvent(self, event: Event) -> None:
        """
        Create an event with the given name.
        """


    @abstractmethod
    async def incidentTypes(
        self, includeHidden: bool = False
    ) -> Iterable[str]:
        """
        Look up the incident types used in this store.
        """


    @abstractmethod
    async def createIncidentType(
        self, incidentType: str, hidden: bool = False
    ) -> None:
        """
        Create the given incident type.
        """


    @abstractmethod
    async def showIncidentTypes(self, incidentTypes: Iterable[str]) -> None:
        """
        Show the given incident types.
        """


    @abstractmethod
    async def hideIncidentTypes(self, incidentTypes: Iterable[str]) -> None:
        """
        Hide the given incident types.
        """


    @abstractmethod
    async def incidents(self, event: Event) -> Iterable[Incident]:
        """
        Look up all incidents for the given event.
        """


    @abstractmethod
    async def incidentWithNumber(self, event: Event, number: int) -> Incident:
        """
        Look up the incident with the given number in the given event.
        """


    @abstractmethod
    async def createIncident(
        self, incident: Incident, author: Ranger
    ) -> Incident:
        """
        Create a new incident and add it into the given event.
        The incident number is determined by the database and must not be
        specified by the given incident.

        The incident's number must be zero, as it will be assigned by the data
        store.

        The stored incident is returned with the incident number assigned to it
        by the data store.
        """
