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

template_setIncidentAttribute = (
    f"""
    update INCIDENT set {{column}} = %(value)s
    where EVENT = ({query_eventID}) and NUMBER = %(incidentNumber)s
    """
)

template_setIncidentReportAttribute = (
    f"""
    update INCIDENT_REPORT set {{column}} = %(value)s
    where NUMBER = %(incidentReportNumber)s
    """
)

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
    createEventOrIgnore=Query(
        "create event if no matching event already exists",
        """
        insert into EVENT (NAME) values (%(eventID)s)
        on duplicate key update NAME=NAME
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
    createIncidentTypeOrIgnore=Query(
        "create incident type if no matching incident type already exists",
        """
        insert into INCIDENT_TYPE (NAME, HIDDEN)
        values (%(incidentType)s, %(hidden)s)
        on duplicate key update NAME=NAME
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
    createConcentricStreetOrIgnore=Query(
        "create concentric street if no matching concentric street already "
        "exists",
        f"""
        insert into CONCENTRIC_STREET (EVENT, ID, NAME)
        values (({query_eventID}), %(streetID)s, %(streetName)s)
        on duplicate key update NAME=NAME
        """
    ),
    detachedReportEntries=Query(
        "look up detached report entries",
        """
        select AUTHOR, TEXT, CREATED, GENERATED from REPORT_ENTRY
        where
            ID not in (select REPORT_ENTRY from INCIDENT__REPORT_ENTRY) and
            ID not in (select REPORT_ENTRY from INCIDENT_REPORT__REPORT_ENTRY)
        """
    ),
    incident=Query(
        "look up incident",
        f"""
        select
            CREATED, PRIORITY, STATE, SUMMARY,
            LOCATION_NAME,
            LOCATION_CONCENTRIC,
            LOCATION_RADIAL_HOUR,
            LOCATION_RADIAL_MINUTE,
            LOCATION_DESCRIPTION
        from INCIDENT i
        where EVENT = ({query_eventID}) and NUMBER = %(incidentNumber)s
        """
    ),
    incident_rangers=Query(
        "look up Ranger for incident",
        f"""
        select RANGER_HANDLE from INCIDENT__RANGER
        where
            EVENT = ({query_eventID}) and INCIDENT_NUMBER = %(incidentNumber)s
        """
    ),
    incident_incidentTypes=Query(
        "look up incident types for incident",
        f"""
        select NAME from INCIDENT_TYPE where ID in (
            select INCIDENT_TYPE from INCIDENT__INCIDENT_TYPE
            where
                EVENT = ({query_eventID}) and
                INCIDENT_NUMBER = %(incidentNumber)s
        )
        """
    ),
    incident_reportEntries=Query(
        "look up report entries for incident",
        f"""
        select AUTHOR, TEXT, CREATED, GENERATED from REPORT_ENTRY
        where ID in (
            select REPORT_ENTRY from INCIDENT__REPORT_ENTRY
            where
                EVENT = ({query_eventID}) and
                INCIDENT_NUMBER = %(incidentNumber)s
        )
        """
    ),
    incidentNumbers=Query(
        "look up incident numbers for event",
        f"""
        select NUMBER from INCIDENT where EVENT = ({query_eventID})
        """
    ),
    maxIncidentNumber=Query(
        "look up maximum incident number for event",
        f"""
        select max(NUMBER) from INCIDENT where EVENT = ({query_eventID})
        """
    ),
    attachRangeHandleToIncident=Query(
        "add Ranger to incident",
        f"""
        insert into INCIDENT__RANGER (EVENT, INCIDENT_NUMBER, RANGER_HANDLE)
        values (({query_eventID}), %(incidentNumber)s, %(rangerHandle)s)
        """
    ),
    attachIncidentTypeToIncident=Query(
        "add incident type to incident",
        f"""
        insert into INCIDENT__INCIDENT_TYPE (
            EVENT, INCIDENT_NUMBER, INCIDENT_TYPE
        )
        values (
            ({query_eventID}),
            %(incidentNumber)s,
            (select ID from INCIDENT_TYPE where NAME = %(incidentType)s)
        )
        """
    ),
    createReportEntry=Query(
        "create report entry",
        """
        insert into REPORT_ENTRY (AUTHOR, TEXT, CREATED, GENERATED, STRICKEN)
        values (%(author)s, %(text)s, %(created)s, %(generated)s, 0)
        """
    ),
    attachReportEntryToIncident=Query(
        "add report entry to incident",
        f"""
        insert into INCIDENT__REPORT_ENTRY (
            EVENT, INCIDENT_NUMBER, REPORT_ENTRY
        )
        values (({query_eventID}), %(incidentNumber)s, %(reportEntryID)s)
        """
    ),
    createIncident=Query(
        "create incident",
        f"""
        insert into INCIDENT (
            EVENT,
            NUMBER,
            VERSION,
            CREATED,
            PRIORITY,
            STATE,
            SUMMARY,
            LOCATION_NAME,
            LOCATION_CONCENTRIC,
            LOCATION_RADIAL_HOUR,
            LOCATION_RADIAL_MINUTE,
            LOCATION_DESCRIPTION
        )
        values (
            ({query_eventID}),
            %(incidentNumber)s,
            1,
            %(incidentCreated)s,
            %(incidentPriority)s,
            %(incidentState)s,
            %(incidentSummary)s,
            %(locationName)s,
            %(locationConcentric)s,
            %(locationRadialHour)s,
            %(locationRadialMinute)s,
            %(locationDescription)s
        )
        """
    ),
    setIncident_priority=Query(
        "set incident priority",
        template_setIncidentAttribute.format(column="PRIORITY")
    ),
    setIncident_state=Query(
        "set incident state",
        template_setIncidentAttribute.format(column="STATE")
    ),
    setIncident_summary=Query(
        "set incident summary",
        template_setIncidentAttribute.format(column="SUMMARY")
    ),
    setIncident_locationName=Query(
        "set incident location name",
        template_setIncidentAttribute.format(column="LOCATION_NAME")
    ),
    setIncident_locationConcentricStreet=Query(
        "set incident location concentric street",
        template_setIncidentAttribute.format(column="LOCATION_CONCENTRIC")
    ),
    setIncident_locationRadialHour=Query(
        "set incident location radial hour",
        template_setIncidentAttribute.format(column="LOCATION_RADIAL_HOUR")
    ),
    setIncident_locationRadialMinute=Query(
        "set incident location radial minute",
        template_setIncidentAttribute.format(column="LOCATION_RADIAL_MINUTE")
    ),
    setIncident_locationDescription=Query(
        "set incident location description",
        template_setIncidentAttribute.format(column="LOCATION_DESCRIPTION")
    ),
    clearIncidentRangers=Query(
        "clear incident Rangers",
        f"""
        delete from INCIDENT__RANGER
        where
            EVENT = ({query_eventID}) and INCIDENT_NUMBER = %(incidentNumber)s
        """
    ),
    clearIncidentIncidentTypes=Query(
        "clear incident types",
        f"""
        delete from INCIDENT__INCIDENT_TYPE
        where
            EVENT = ({query_eventID}) and INCIDENT_NUMBER = %(incidentNumber)s
        """
    ),
    incidentReport=Query(
        "look up incident report",
        """
        select CREATED, SUMMARY from INCIDENT_REPORT
        where NUMBER = %(incidentReportNumber)s
        """
    ),
    incidentReport_reportEntries=Query(
        "look up report entries for incident report",
        """
        select AUTHOR, TEXT, CREATED, GENERATED from REPORT_ENTRY
        where ID in (
            select REPORT_ENTRY from INCIDENT_REPORT__REPORT_ENTRY
            where INCIDENT_REPORT_NUMBER = %(incidentReportNumber)s
        )
        """
    ),
    incidentReportNumbers=Query(
        "look up incident report numbers for event",
        f"""
        select NUMBER from INCIDENT_REPORT
        where NUMBER in (
            select INCIDENT_REPORT_NUMBER from INCIDENT__INCIDENT_REPORT
            where
                EVENT = ({query_eventID})
        )
        """
    ),
    maxIncidentReportNumber=Query(
        "look up maximum incident report number",
        """
        select max(NUMBER) from INCIDENT_REPORT
        """
    ),
    createIncidentReport=Query(
        "create incident report",
        """
        insert into INCIDENT_REPORT (NUMBER, CREATED, SUMMARY)
        values (
            %(incidentReportNumber)s,
            %(incidentReportCreated)s,
            %(incidentReportSummary)s
        )
        """
    ),
    attachReportEntryToIncidentReport=Query(
        "add report entry to incident report",
        """
        insert into INCIDENT_REPORT__REPORT_ENTRY (
            INCIDENT_REPORT_NUMBER, REPORT_ENTRY
        )
        values (%(incidentReportNumber)s, %(reportEntryID)s)
        """
    ),
    setIncidentReport_summary=Query(
        "set incident report summary",
        template_setIncidentReportAttribute.format(column="SUMMARY")
    ),
    detachedIncidentReportNumbers=Query(
        "look up detached incident report numbers",
        """
        select NUMBER from INCIDENT_REPORT
        where NUMBER not in (
            select INCIDENT_REPORT_NUMBER from INCIDENT__INCIDENT_REPORT
        )
        """
    ),
    attachedIncidentReportNumbers=Query(
        "look up attached incident report numbers",
        f"""
        select NUMBER from INCIDENT_REPORT
        where NUMBER in (
            select INCIDENT_REPORT_NUMBER from INCIDENT__INCIDENT_REPORT
            where
                EVENT = ({query_eventID}) and
                INCIDENT_NUMBER = %(incidentNumber)s
        )
        """
    ),
    incidentsAttachedToIncidentReport=Query(
        "look up incidents attached to incident report",
        """
        select e.NAME as EVENT, iir.INCIDENT_NUMBER as INCIDENT_NUMBER
        from INCIDENT__INCIDENT_REPORT iir
        join EVENT e on e.ID = iir.EVENT
        where iir.INCIDENT_REPORT_NUMBER = %(incidentReportNumber)s
        """
    ),
    attachIncidentReportToIncident=Query(
        "add incident report to incident",
        f"""
        insert into INCIDENT__INCIDENT_REPORT (
            EVENT, INCIDENT_NUMBER, INCIDENT_REPORT_NUMBER
        )
        values (
            ({query_eventID}), %(incidentNumber)s, %(incidentReportNumber)s
        )
        """
    ),
    detachIncidentReportFromIncident=Query(
        "remove incident report from incident",
        f"""
        delete from INCIDENT__INCIDENT_REPORT
        where
            EVENT = ({query_eventID}) and
            INCIDENT_NUMBER = %(incidentNumber)s and
            INCIDENT_REPORT_NUMBER = %(incidentReportNumber)s
        """
    ),
)
