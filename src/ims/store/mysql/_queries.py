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
Incident Management System SQLite queries.
"""

from .._db import Queries, Query


__all__ = ()


query_eventID = "select ID from EVENT where NAME = %(eventID)s"

queries = Queries(
    schemaVersion=Query(
        "look up schema version",
        """
        select VERSION from SCHEMA_INFO
        """
    ),
    events=Query(
        "look up events",
        """
        select NAME from EVENT
        """
    ),
    createEvent=Query(
        "create event",
        """
        insert into EVENT (NAME) values (%(eventID)s)
        """
    ),
    eventAccess=Query(
        "look up event access",
        f"""
        select EXPRESSION from EVENT_ACCESS
        where EVENT = ({query_eventID}) and MODE = %(mode)s
        """
    ),
    clearEventAccessForMode=Query(
        "clear event access for mode",
        f"""
        delete from EVENT_ACCESS
        where EVENT = ({query_eventID}) and MODE = %(mode)s
        """
    ),
    clearEventAccessForExpression=Query(
        "clear event access for expression",
        f"""
        delete from EVENT_ACCESS
        where EVENT = ({query_eventID}) and EXPRESSION = %(expression)s
        """
    ),
    addEventAccess=Query(
        "add event access",
        f"""
        insert into EVENT_ACCESS (EVENT, EXPRESSION, MODE)
        values (({query_eventID}), %(expression)s, %(mode)s)
        """
    ),

    incidentTypes=Query(
        "look up incident types",
        """
        select NAME from INCIDENT_TYPE
        """
    ),
    incidentTypesNotHidden=Query(
        "look up non-hidden incident types",
        """
        select NAME from INCIDENT_TYPE where HIDDEN = 0
        """
    ),
    createIncidentType=Query(
        "create incident type",
        """
        insert into INCIDENT_TYPE (NAME, HIDDEN)
        values (%(incidentType)s, %(hidden)s)
        """
    ),
    hideShowIncidentType=Query(
        "hide/show incident type",
        """
        update INCIDENT_TYPE set HIDDEN = %(hidden)s
        where NAME = %(incidentType)s
        """
    ),
    concentricStreets=Query(
        "look up concentric streets for event",
        f"""
        select ID, NAME from CONCENTRIC_STREET
        where EVENT = ({query_eventID})
        """
    ),
    createConcentricStreet=Query(
        "create concentric street",
        f"""
        insert into CONCENTRIC_STREET (EVENT, ID, NAME)
        values (({query_eventID}), %(streetID)s, %(streetName)s)
        """
    ),

    # ****************** Not done yet ******************

    detachedReportEntries=Query(
        "look up detached report entries",
        """
        """
    ),
    incident=Query(
        "look up incident",
        """
        """
    ),
    incident_rangers=Query(
        "look up Ranger for incident",
        """
        """
    ),
    incident_incidentTypes=Query(
        "look up incident types for incident",
        """
        """
    ),
    incident_reportEntries=Query(
        "look up report entries for incident",
        """
        """
    ),
    incidentNumbers=Query(
        "look up incident numbers for event",
        """
        """
    ),
    maxIncidentNumber=Query(
        "look up maximum incident number for event",
        """
        """
    ),
    attachRangeHandleToIncident=Query(
        "add Ranger to incident",
        """
        """
    ),
    attachIncidentTypeToIncident=Query(
        "add incident type to incident",
        """
        """
    ),
    createReportEntry=Query(
        "create report entry",
        """
        """
    ),
    attachReportEntryToIncident=Query(
        "add report entry to incident",
        """
        """
    ),
    createIncident=Query(
        "create incident",
        """
        """
    ),
    setIncident_priority=Query(
        "set incident priority",
        """
        """
    ),
    setIncident_state=Query(
        "set incident state",
        """
        """
    ),
    setIncident_summary=Query(
        "set incident summary",
        """
        """
    ),
    setIncident_locationName=Query(
        "set incident location name",
        """
        """
    ),
    setIncident_locationConcentricStreet=Query(
        "set incident location concentric street",
        """
        """
    ),
    setIncident_locationRadialHour=Query(
        "set incident location radial hour",
        """
        """
    ),
    setIncident_locationRadialMinute=Query(
        "set incident location radial minute",
        """
        """
    ),
    setIncident_locationDescription=Query(
        "set incident location description",
        """
        """
    ),
    clearIncidentRangers=Query(
        "clear incident Rangers",
        """
        """
    ),
    clearIncidentIncidentTypes=Query(
        "clear incident types",
        """
        """
    ),
    incidentReport=Query(
        "look up incident report",
        """
        """
    ),
    incidentReport_reportEntries=Query(
        "look up report entries for incident report",
        """
        """
    ),
    incidentReportNumbers=Query(
        "look up incident report numbers",
        """
        """
    ),
    maxIncidentReportNumber=Query(
        "look up maximum incident report number",
        """
        """
    ),
    createIncidentReport=Query(
        "create incident report",
        """
        """
    ),
    attachReportEntryToIncidentReport=Query(
        "add report entry to incident report",
        """
        """
    ),
    setIncidentReport_summary=Query(
        "set incident report summary",
        """
        """
    ),
    detachedIncidentReportNumbers=Query(
        "look up detached incident report numbers",
        """
        """
    ),
    attachedIncidentReportNumbers=Query(
        "look up attached incident report numbers",
        """
        """
    ),
    incidentsAttachedToIncidentReport=Query(
        "look up incidents attached to incident report",
        """
        """
    ),
    attachIncidentReportToIncident=Query(
        "add incident report to incident",
        """
        """
    ),
    detachIncidentReportFromIncident=Query(
        "remove incident report from incident",
        """
        """
    ),
)
