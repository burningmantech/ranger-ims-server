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
from typing import Iterable, Mapping

from ims.model import (
    Event, Incident, IncidentPriority, IncidentReport, IncidentState
)


__all__ = ()



class IMSDataStore(ABC):
    """
    Incident Management System data store abstract base class.
    """

    ###
    # Events
    ###


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
    async def readers(self, event: Event) -> Iterable[str]:
        """
        Look up the allowed readers for the given event.
        """


    @abstractmethod
    def setReaders(self, event: Event, readers: Iterable[str]) -> None:
        """
        Set the allowed readers for the given event.
        """


    @abstractmethod
    def writers(self, event: Event) -> Iterable[str]:
        """
        Look up the allowed writers for the given event.
        """


    @abstractmethod
    def setWriters(self, event: Event, writers: Iterable[str]) -> None:
        """
        Set the allowed writers for the given event.
        """


    ###
    # Incident Types
    ###


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


    ###
    # Concentric Streets
    ###


    @abstractmethod
    async def concentricStreets(self, event: Event) -> Mapping[str, str]:
        """
        Look up the concentric streets associated with the given event.
        Returns a mapping from street ID to street name.
        """


    @abstractmethod
    async def createConcentricStreet(
        self, event: Event, id: str, name: str
    ) -> None:
        """
        Create a new concentric street and associated it with the given event.
        """


    ###
    # Incidents
    ###


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
        self, incident: Incident, author: str
    ) -> Incident:
        """
        Create a new incident and add it into the given event.

        The incident number is determined by the database and must not be
        specified by the given incident.

        The incident's number must be zero, as it will be assigned by the data
        store.

        The stored incident is returned with the incident number assigned to it
        by the data store, and with initial (automatic) report entries added.
        """


    @abstractmethod
    async def importIncident(self, incident: Incident) -> None:
        """
        Import an incident and add it into the given event.

        This differs from :meth:`IMSDataStore.createIncident` in that the
        incident is added exactly as is; the incident's number is not modified
        (and must be greater than zero), and no automatic entries are added to
        it.
        """


    @abstractmethod
    async def setIncidentPriority(
        self, event: Event, incidentNumber: int, priority: IncidentPriority,
        author: str,
    ) -> None:
        """
        Set the priority for the incident with the given number in the given
        event.
        """


    @abstractmethod
    async def setIncidentState(
        self, event: Event, incidentNumber: int, state: IncidentState,
        author: str,
    ) -> None:
        """
        Set the state for the given incident in the given event.
        """


    @abstractmethod
    async def setIncidentSummary(
        self, event: Event, incidentNumber: int, summary: str, author: str
    ) -> None:
        """
        Set the summary for the given incident in the given event.
        """


    @abstractmethod
    async def setIncidentLocationName(
        self, event: Event, incidentNumber: int, name: str, author: str
    ) -> None:
        """
        Set the location name for the given incident in the given event.
        """


    @abstractmethod
    async def setIncidentLocationConcentricStreet(
        self, event: Event, incidentNumber: int, streetID: str, author: str
    ) -> None:
        """
        Set the location concentric street for the given incident in the given
        event.
        """


    @abstractmethod
    async def setIncidentLocationRadialHour(
        self, event: Event, incidentNumber: int, hour: int, author: str
    ) -> None:
        """
        Set the location radial hour for the given incident in the given event.
        """


    @abstractmethod
    async def setIncidentLocationRadialMinute(
        self, event: Event, incidentNumber: int, minute: int, author: str
    ) -> None:
        """
        Set the location radial minute for the given incident in the given
        event.
        """


    @abstractmethod
    async def setIncidentLocationDescription(
        self, event: Event, incidentNumber: int, description: str, author: str
    ) -> None:
        """
        Set the location description for the given incident in the given event.
        """


    ###
    # Incident Reports
    ###


    @abstractmethod
    async def incidentReports(self) -> Iterable[IncidentReport]:
        """
        Look up all incident reports.
        """


    @abstractmethod
    async def detachedIncidentReports(self) -> Iterable[IncidentReport]:
        """
        Look up all detached incident reports.
        """


    @abstractmethod
    async def attachedIncidentReports(
        self, event: Event, incidentNumber: int
    ) -> Iterable[IncidentReport]:
        """
        Look up all incident reports attached to the given incident in the
        given event.
        """


    @abstractmethod
    async def incidentReportWithNumber(self, number: int) -> IncidentReport:
        """
        Look up the incident report with the given number.
        """
