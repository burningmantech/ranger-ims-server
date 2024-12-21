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
from collections.abc import Iterable, Mapping

from ims.model import (
    Event,
    FieldReport,
    Incident,
    IncidentPriority,
    IncidentState,
    ReportEntry,
)


__all__ = ()


class IMSDataStore(ABC):
    """
    Incident Management System data store abstract base class.
    """

    ##
    # Database management
    ##

    @abstractmethod
    async def upgradeSchema(self) -> None:
        """
        Upgrade the data store schema to the current version.
        """

    @abstractmethod
    async def validate(self) -> None:
        """
        Perform some data integrity checks and raise :exc:`StorageError` if
        there are any problems detected.
        """

    ###
    # Incident Types
    ###

    @abstractmethod
    async def incidentTypes(self, *, includeHidden: bool = False) -> Iterable[str]:
        """
        Look up the incident types used in this store.
        """

    @abstractmethod
    async def createIncidentType(
        self, incidentType: str, *, hidden: bool = False
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
        Create the given event.
        """

    @abstractmethod
    async def readers(self, eventID: str) -> Iterable[str]:
        """
        Look up the allowed readers for the given event.
        """

    @abstractmethod
    async def setReaders(self, eventID: str, readers: Iterable[str]) -> None:
        """
        Set the allowed readers for the given event.
        """

    @abstractmethod
    async def writers(self, eventID: str) -> Iterable[str]:
        """
        Look up the allowed writers for the given event.
        """

    @abstractmethod
    async def setWriters(self, eventID: str, writers: Iterable[str]) -> None:
        """
        Set the allowed writers for the given event.
        """

    @abstractmethod
    async def reporters(self, eventID: str) -> Iterable[str]:
        """
        Look up the allowed reporters for the given event.
        """

    @abstractmethod
    async def setReporters(self, eventID: str, writers: Iterable[str]) -> None:
        """
        Set the allowed reporters for the given event.
        """

    ###
    # Concentric Streets
    ###

    @abstractmethod
    async def concentricStreets(self, eventID: str) -> Mapping[str, str]:
        """
        Look up the concentric streets associated with the given event.
        Returns a mapping from street ID to street name.
        """

    @abstractmethod
    async def createConcentricStreet(self, eventID: str, id: str, name: str) -> None:
        """
        Create a new concentric street and associated it with the given event.
        """

    ###
    # Incidents
    ###

    @abstractmethod
    async def incidents(
        self, eventID: str, *, excludeSystemEntries: bool = False
    ) -> Iterable[Incident]:
        """
        Look up all incidents for the given event.
        """

    @abstractmethod
    async def incidentWithNumber(self, eventID: str, number: int) -> Incident:
        """
        Look up the incident with the given number in the given event.
        """

    @abstractmethod
    async def createIncident(self, incident: Incident, author: str) -> Incident:
        """
        Create a new incident and add it into the event referenced by the
        incident.

        The incident number is determined by the database and must be specified
        as zero in the given incident.

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
    async def setIncident_priority(
        self,
        eventID: str,
        incidentNumber: int,
        priority: IncidentPriority,
        author: str,
    ) -> None:
        """
        Set the priority for the incident with the given number in the given
        event.
        """

    @abstractmethod
    async def setIncident_state(
        self,
        eventID: str,
        incidentNumber: int,
        state: IncidentState,
        author: str,
    ) -> None:
        """
        Set the state for the incident with the given number in the given
        event.
        """

    @abstractmethod
    async def setIncident_summary(
        self, eventID: str, incidentNumber: int, summary: str, author: str
    ) -> None:
        """
        Set the summary for the incident with the given number in the given
        event.
        """

    @abstractmethod
    async def setIncident_locationName(
        self, eventID: str, incidentNumber: int, name: str, author: str
    ) -> None:
        """
        Set the location name for the incident with the given number in the
        given event.
        """

    @abstractmethod
    async def setIncident_locationConcentricStreet(
        self, eventID: str, incidentNumber: int, streetID: str, author: str
    ) -> None:
        """
        Set the location concentric street for the incident with the given
        number in the given event.
        """

    @abstractmethod
    async def setIncident_locationRadialHour(
        self, eventID: str, incidentNumber: int, hour: int, author: str
    ) -> None:
        """
        Set the location radial hour for the incident with the given number in
        the given event.
        """

    @abstractmethod
    async def setIncident_locationRadialMinute(
        self, eventID: str, incidentNumber: int, minute: int, author: str
    ) -> None:
        """
        Set the location radial minute for the incident with the given number
        in the given event.
        """

    @abstractmethod
    async def setIncident_locationDescription(
        self, eventID: str, incidentNumber: int, description: str, author: str
    ) -> None:
        """
        Set the location description for the incident with the given number in
        the given event.
        """

    @abstractmethod
    async def setIncident_rangers(
        self,
        eventID: str,
        incidentNumber: int,
        rangerHandles: Iterable[str],
        author: str,
    ) -> None:
        """
        Set the Rangers attached to the incident with the given number in the
        given event.
        """

    @abstractmethod
    async def setIncident_incidentTypes(
        self,
        eventID: str,
        incidentNumber: int,
        incidentTypes: Iterable[str],
        author: str,
    ) -> None:
        """
        Set the incident types attached to the incident with the given number
        in the given event.
        """

    @abstractmethod
    async def addReportEntriesToIncident(
        self,
        eventID: str,
        incidentNumber: int,
        reportEntries: Iterable[ReportEntry],
        author: str,
    ) -> None:
        """
        Add the given report entries to incident with the given number in the
        given event.
        """

    ###
    # Field Reports
    ###

    @abstractmethod
    async def fieldReports(
        self, eventID: str, *, excludeSystemEntries: bool = False
    ) -> Iterable[FieldReport]:
        """
        Look up all field reports in the given event.
        """

    @abstractmethod
    async def fieldReportWithNumber(self, eventID: str, number: int) -> FieldReport:
        """
        Look up the field report with the given number.
        """

    @abstractmethod
    async def createFieldReport(
        self, fieldReport: FieldReport, author: str
    ) -> FieldReport:
        """
        Create a new field report.

        The field report number is determined by the database and must be
        specified as zero in the given field report.

        The stored field report is returned with the field report number
        assigned to it by the data store, and with initial (automatic) report
        entries added.
        """

    @abstractmethod
    async def importFieldReport(self, fieldReport: FieldReport) -> None:
        """
        Import a field report and add it into the given event.

        This differs from :meth:`IMSDataStore.createFieldReport` in that the
        field report is added exactly as is; the field report's number is
        not modified (and must be greater than zero), and no automatic entries
        are added to it.
        """

    @abstractmethod
    async def setFieldReport_summary(
        self,
        eventID: str,
        fieldReportNumber: int,
        summary: str,
        author: str,
    ) -> None:
        """
        Set the summary for the field report with the given number.
        """

    @abstractmethod
    async def addReportEntriesToFieldReport(
        self,
        eventID: str,
        fieldReportNumber: int,
        reportEntries: Iterable[ReportEntry],
        author: str,
    ) -> None:
        """
        Add the given report entries to field report with the given number.
        """

    ###
    # Incident to Field Report Relationships
    ###

    @abstractmethod
    async def fieldReportsAttachedToIncident(
        self, eventID: str, incidentNumber: int
    ) -> Iterable[FieldReport]:
        """
        Look up all field reports attached to the incident with the given
        number in the given event.
        """

    @abstractmethod
    async def attachFieldReportToIncident(
        self,
        fieldReportNumber: int,
        eventID: str,
        incidentNumber: int,
        author: str,
    ) -> None:
        """
        Attach the field report with the given number to the incident with
        the given number in the given event.
        """

    @abstractmethod
    async def detachFieldReportFromIncident(
        self,
        fieldReportNumber: int,
        eventID: str,
        incidentNumber: int,
        author: str,
    ) -> None:
        """
        Detach the field report with the given number from the incident with
        the given number in the given event.
        """
