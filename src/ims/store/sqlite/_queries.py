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


query_eventID = "select ID from EVENT where NAME = :eventID"

template_setIncidentAttribute = f"""
    update INCIDENT set {{column}} = :value
    where EVENT = ({query_eventID}) and NUMBER = :incidentNumber
    """

template_setIncidentReportAttribute = f"""
    update INCIDENT_REPORT set {{column}} = :value
    where EVENT = ({query_eventID}) and NUMBER = :incidentReportNumber
    """

queries = Queries(
    schemaVersion=Query(
        "look up schema version",
        """
        select VERSION from SCHEMA_INFO
        """,
    ),
    events=Query(
        "look up events",
        """
        select NAME from EVENT
        """,
    ),
    createEvent=Query(
        "create event",
        """
        insert into EVENT (NAME) values (:eventID)
        """,
    ),
    createEventOrIgnore=Query(
        "create event if no matching event already exists",
        """
        insert or ignore into EVENT (NAME) values (:eventID)
        """,
    ),
    eventAccess=Query(
        "look up access for event",
        f"""
        select EXPRESSION from EVENT_ACCESS
        where EVENT = ({query_eventID}) and MODE = :mode
        """,
    ),
    clearEventAccessForMode=Query(
        "clear event access for mode",
        f"""
        delete from EVENT_ACCESS
        where EVENT = ({query_eventID}) and MODE = :mode
        """,
    ),
    clearEventAccessForExpression=Query(
        "clear event access for expression",
        f"""
        delete from EVENT_ACCESS
        where EVENT = ({query_eventID}) and EXPRESSION = :expression
        """,
    ),
    addEventAccess=Query(
        "add event access",
        f"""
        insert into EVENT_ACCESS (EVENT, EXPRESSION, MODE)
        values (({query_eventID}), :expression, :mode)
        """,
    ),
    incidentTypes=Query(
        "look up incident types",
        """
        select NAME from INCIDENT_TYPE
        """,
    ),
    incidentTypesNotHidden=Query(
        "look up non-hidden incident types",
        """
        select NAME from INCIDENT_TYPE where HIDDEN = 0
        """,
    ),
    createIncidentType=Query(
        "create incident type",
        """
        insert into INCIDENT_TYPE (NAME, HIDDEN)
        values (:incidentType, :hidden)
        """,
    ),
    createIncidentTypeOrIgnore=Query(
        "create incident type if no matching incident type already exists",
        """
        insert or ignore into INCIDENT_TYPE (NAME, HIDDEN)
        values (:incidentType, :hidden)
        """,
    ),
    hideShowIncidentType=Query(
        "hide/show incident type",
        """
        update INCIDENT_TYPE set HIDDEN = :hidden
        where NAME = :incidentType
        """,
    ),
    concentricStreets=Query(
        "look up concentric streets for event",
        f"""
        select ID, NAME from CONCENTRIC_STREET
        where EVENT = ({query_eventID})
        """,
    ),
    createConcentricStreet=Query(
        "create concentric street",
        f"""
        insert into CONCENTRIC_STREET (EVENT, ID, NAME)
        values (({query_eventID}), :streetID, :streetName)
        """,
    ),
    createConcentricStreetOrIgnore=Query(
        "create concentric street if no matching concentric street already "
        "exists",
        f"""
        insert or ignore into CONCENTRIC_STREET (EVENT, ID, NAME)
        values (({query_eventID}), :streetID, :streetName)
        """,
    ),
    detachedReportEntries=Query(
        "look up detached report entries",
        """
        select AUTHOR, TEXT, CREATED, GENERATED from REPORT_ENTRY
        where
            ID not in (select REPORT_ENTRY from INCIDENT__REPORT_ENTRY) and
            ID not in (select REPORT_ENTRY from INCIDENT_REPORT__REPORT_ENTRY)
        """,
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
        where EVENT = ({query_eventID}) and NUMBER = :incidentNumber
        """,
    ),
    incident_rangers=Query(
        "look up Ranger for incident",
        f"""
        select RANGER_HANDLE from INCIDENT__RANGER
        where EVENT = ({query_eventID}) and INCIDENT_NUMBER = :incidentNumber
        """,
    ),
    incident_incidentTypes=Query(
        "look up incident types for incident",
        f"""
        select NAME from INCIDENT_TYPE where ID in (
            select INCIDENT_TYPE from INCIDENT__INCIDENT_TYPE
            where
                EVENT = ({query_eventID}) and INCIDENT_NUMBER = :incidentNumber
        )
        """,
    ),
    incident_reportEntries=Query(
        "look up report entries for incident",
        f"""
        select AUTHOR, TEXT, CREATED, GENERATED from REPORT_ENTRY
        where ID in (
            select REPORT_ENTRY from INCIDENT__REPORT_ENTRY
            where
                EVENT = ({query_eventID}) and INCIDENT_NUMBER = :incidentNumber
        )
        """,
    ),
    incidentNumbers=Query(
        "look up incident numbers for event",
        f"""
        select NUMBER from INCIDENT where EVENT = ({query_eventID})
        """,
    ),
    maxIncidentNumber=Query(
        "look up maximum incident number for event",
        f"""
        select max(NUMBER) from INCIDENT where EVENT = ({query_eventID})
        """,
    ),
    incidents=Query(
        "look up incidents for event",
        f"""
        select
            i.NUMBER,
            i.CREATED,
            i.PRIORITY,
            i.STATE,
            i.SUMMARY,
            i.LOCATION_NAME,
            i.LOCATION_CONCENTRIC,
            i.LOCATION_RADIAL_HOUR,
            i.LOCATION_RADIAL_MINUTE,
            i.LOCATION_DESCRIPTION,
            i.EVENT,
            (
                select json_group_array(it.NAME)
                from INCIDENT__INCIDENT_TYPE iit
                join INCIDENT_TYPE it
                    on i.EVENT = iit.EVENT
                    and i.NUMBER = iit.INCIDENT_NUMBER
                    and iit.INCIDENT_TYPE = it.ID
            ) as INCIDENT_TYPES,
            (
                select json_group_array(irep.NUMBER)
                from INCIDENT_REPORT irep
                where i.EVENT = irep.EVENT
                    and i.NUMBER = irep.INCIDENT_NUMBER
            ) as INCIDENT_REPORT_NUMBERS,
            (
                select json_group_array(ir.RANGER_HANDLE)
                from INCIDENT__RANGER ir
                where i.EVENT = ir.EVENT
                    and i.NUMBER = ir.INCIDENT_NUMBER
            ) as RANGER_HANDLES
        from
            INCIDENT i
        where
            i.EVENT = ({query_eventID})
        group by
            i.NUMBER
        """,
    ),
    incidents_reportEntries=Query(
        "look up report entries for all incidents in an event",
        f"""
        select
            ire.INCIDENT_NUMBER,
            re.AUTHOR,
            re.TEXT,
            re.CREATED,
            re.GENERATED
        from
            INCIDENT__REPORT_ENTRY ire
            join REPORT_ENTRY re
                on re.ID = ire.REPORT_ENTRY
        where
            ire.EVENT = ({query_eventID})
        ;
        """,
    ),
    attachRangeHandleToIncident=Query(
        "add Ranger to incident",
        f"""
        insert into INCIDENT__RANGER (EVENT, INCIDENT_NUMBER, RANGER_HANDLE)
        values (({query_eventID}), :incidentNumber, :rangerHandle)
        """,
    ),
    attachIncidentTypeToIncident=Query(
        "add incident type to incident",
        f"""
        insert into INCIDENT__INCIDENT_TYPE (
            EVENT, INCIDENT_NUMBER, INCIDENT_TYPE
        )
        values (
            ({query_eventID}),
            :incidentNumber,
            (select ID from INCIDENT_TYPE where NAME = :incidentType)
        )
        """,
    ),
    createReportEntry=Query(
        "create report entry",
        """
        insert into REPORT_ENTRY (AUTHOR, TEXT, CREATED, GENERATED, STRICKEN)
        values (:author, :text, :created, :generated, 0)
        """,
    ),
    attachReportEntryToIncident=Query(
        "add report entry to incident",
        f"""
        insert into INCIDENT__REPORT_ENTRY (
            EVENT, INCIDENT_NUMBER, REPORT_ENTRY
        )
        values (({query_eventID}), :incidentNumber, :reportEntryID)
        """,
    ),
    createIncident=Query(
        "create incident",
        f"""
        insert into INCIDENT (
            EVENT,
            NUMBER,
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
            :incidentNumber,
            :incidentCreated,
            :incidentPriority,
            :incidentState,
            :incidentSummary,
            :locationName,
            :locationConcentric,
            :locationRadialHour,
            :locationRadialMinute,
            :locationDescription
        )
        """,
    ),
    setIncident_priority=Query(
        "set incident priority",
        template_setIncidentAttribute.format(column="PRIORITY"),
    ),
    setIncident_state=Query(
        "set incident state",
        template_setIncidentAttribute.format(column="STATE"),
    ),
    setIncident_summary=Query(
        "set incident summary",
        template_setIncidentAttribute.format(column="SUMMARY"),
    ),
    setIncident_locationName=Query(
        "set incident location name",
        template_setIncidentAttribute.format(column="LOCATION_NAME"),
    ),
    setIncident_locationConcentricStreet=Query(
        "set incident location concentric street",
        template_setIncidentAttribute.format(column="LOCATION_CONCENTRIC"),
    ),
    setIncident_locationRadialHour=Query(
        "set incident location radial hour",
        template_setIncidentAttribute.format(column="LOCATION_RADIAL_HOUR"),
    ),
    setIncident_locationRadialMinute=Query(
        "set incident location radial minute",
        template_setIncidentAttribute.format(column="LOCATION_RADIAL_MINUTE"),
    ),
    setIncident_locationDescription=Query(
        "set incident location description",
        template_setIncidentAttribute.format(column="LOCATION_DESCRIPTION"),
    ),
    clearIncidentRangers=Query(
        "clear incident Rangers",
        f"""
        delete from INCIDENT__RANGER
        where EVENT = ({query_eventID}) and INCIDENT_NUMBER = :incidentNumber
        """,
    ),
    clearIncidentIncidentTypes=Query(
        "clear incident types",
        f"""
        delete from INCIDENT__INCIDENT_TYPE
        where EVENT = ({query_eventID}) and INCIDENT_NUMBER = :incidentNumber
        """,
    ),
    incidentReport=Query(
        "look up incident report",
        f"""
        select CREATED, SUMMARY, INCIDENT_NUMBER from INCIDENT_REPORT
        where EVENT = ({query_eventID}) and NUMBER = :incidentReportNumber
        """,
    ),
    incidentReport_reportEntries=Query(
        "look up report entries for incident report",
        f"""
        select AUTHOR, TEXT, CREATED, GENERATED from REPORT_ENTRY
        where ID in (
            select REPORT_ENTRY from INCIDENT_REPORT__REPORT_ENTRY
            where
                EVENT = ({query_eventID}) and
                INCIDENT_REPORT_NUMBER = :incidentReportNumber
        )
        """,
    ),
    incidentReportNumbers=Query(
        "look up incident report numbers for event",
        f"""
        select NUMBER from INCIDENT_REPORT
        where EVENT = ({query_eventID})
        """,
    ),
    maxIncidentReportNumber=Query(
        "look up maximum incident report number",
        """
        select max(NUMBER) from INCIDENT_REPORT
        """,
    ),
    incidentReports=Query(
        "look up all incident reports for an event",
        f"""
        select
            NUMBER,
            CREATED,
            SUMMARY,
            INCIDENT_NUMBER
        from
            INCIDENT_REPORT
        where
            EVENT = ({query_eventID})
        """,
    ),
    incidentReports_reportEntries=Query(
        "look up all incident report report entries for an event",
        f"""
        select
            irre.INCIDENT_REPORT_NUMBER,
            re.AUTHOR,
            re.CREATED,
            re.GENERATED,
            re.ID,
            re.TEXT
        from
            INCIDENT_REPORT__REPORT_ENTRY irre
            join REPORT_ENTRY re
                on irre.REPORT_ENTRY = re.ID
        where
            irre.EVENT = ({query_eventID})
        """,
    ),
    createIncidentReport=Query(
        "create incident report",
        f"""
        insert into INCIDENT_REPORT (
            EVENT, NUMBER, CREATED, SUMMARY, INCIDENT_NUMBER
        )
        values (
            ({query_eventID}),
            :incidentReportNumber,
            :incidentReportCreated,
            :incidentReportSummary,
            :incidentNumber
        )
        """,
    ),
    attachReportEntryToIncidentReport=Query(
        "add report entry to incident report",
        f"""
        insert into INCIDENT_REPORT__REPORT_ENTRY (
            EVENT, INCIDENT_REPORT_NUMBER, REPORT_ENTRY
        )
        values (({query_eventID}), :incidentReportNumber, :reportEntryID)
        """,
    ),
    setIncidentReport_summary=Query(
        "set incident report summary",
        template_setIncidentReportAttribute.format(column="SUMMARY"),
    ),
    attachIncidentReportToIncident=Query(
        "attach incident report to incident",
        template_setIncidentReportAttribute.format(column="INCIDENT_NUMBER"),
    ),
    detachedIncidentReportNumbers=Query(
        "look up detached incident report numbers",
        f"""
        select NUMBER from INCIDENT_REPORT
        where EVENT = ({query_eventID}) and INCIDENT_NUMBER is null
        """,
    ),
    attachedIncidentReportNumbers=Query(
        "look up attached incident report numbers",
        f"""
        select NUMBER from INCIDENT_REPORT
        where EVENT = ({query_eventID}) and INCIDENT_NUMBER = :incidentNumber
        """,
    ),
)
