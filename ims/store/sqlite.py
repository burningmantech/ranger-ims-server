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
Incident Management System SQLite data store.
"""

from __future__ import print_function

__all__ = [
    "Storage"
]

from textwrap import dedent
from datetime import datetime as DateTime, timedelta as TimeDelta
from calendar import timegm
from sqlite3 import (
    connect, Row as LameRow, OperationalError, Error as SQLiteError
)

from twisted.python.filepath import FilePath
from twisted.logger import Logger

from ..tz import utc, utcNow
from ..data.model import (
    Incident, IncidentState, Ranger, ReportEntry,
    Location, RodGarettAddress,
    InvalidDataError,
)
from ._file import MultiStorage
from .istore import StorageError



def _query(query):
    return dedent(query.format(
        query_eventID="select ID from EVENT where NAME = ?",
    ))



class Storage(object):
    """
    SQLite-backed storage.
    """

    log = Logger()


    @classmethod
    def printSchema(cls):
        with createDB() as db:
            printSchema(db)


    @classmethod
    def printQueries(cls):
        storage = cls(None)
        for line in storage.explainQueryPlans():
            print(line)
            print()


    def __init__(self, dbFilePath):
        self.dbFilePath = dbFilePath


    @property
    def _db(self):
        if not hasattr(self, "_connection"):
            try:
                db = openDB(self.dbFilePath, create=True)
                db.execute("pragma foreign_keys = ON")
            except SQLiteError as e:
                raise StorageError(e)
            self._connection = db

        return self._connection


    def loadFromFileStore(self, filePath):
        """
        Load data from a legacy file store.
        """
        self.log.info(
            "Loading data from file store: {filePath.path}", filePath=filePath
        )
        multiStore = MultiStorage(filePath, readOnly=True)

        # Iterate through each event
        for event in multiStore:
            self.log.info("Creating event: {event}", event=event)
            self.createEvent(event)

            eventStore = multiStore[event]

            # Load concentric street names
            for name, id in eventStore.streetsByName().items():
                self.log.info(
                    "Creating concentric street: {event}: {name}",
                    event=event, name=name
                )
                self.createConcentricStreet(event, id, name)

            # Load incidents
            for number, etag in eventStore.listIncidents():
                incident = eventStore.readIncidentWithNumber(number)

                for incidentType in incident.incidentTypes:
                    self.createIncidentType(incidentType, hidden=True)

                self.log.info(
                    "Creating incident: {incident}", incident=incident
                )
                self.importIncident(event, incident)

            # Load access
            self.setReaders(event, eventStore.readers())
            self.setWriters(event, eventStore.writers())


    def events(self):
        """
        Look up all events in this store.
        """
        try:
            for row in self._db.execute(self._query_events):
                yield row["name"]
        except SQLiteError as e:
            self.log.critical("Unable to look up events")
            raise StorageError(e)

    _query_events = dedent(
        """
        select NAME from EVENT
        """
    )

    def createEvent(self, event):
        """
        Create an event with the given name.
        """
        try:
            with self._db as db:
                db.execute(self._query_createEvent, (event,))
        except SQLiteError as e:
            self.log.critical("Unable to create event: {event}", event=event)
            raise StorageError(e)

    _query_createEvent = dedent(
        """
        insert or ignore into EVENT (NAME) values (?)
        """
    )


    def allIncidentTypes(self, includeHidden=False):
        """
        Look up the incident types used in this store.
        """
        if includeHidden:
            query = self._query_incidentTypes
        else:
            query = self._query_incidentTypesNotHidden

        try:
            for row in self._db.execute(query):
                yield row["NAME"]
        except SQLiteError as e:
            self.log.critical("Unable to look up incident types")
            raise StorageError(e)


    _query_incidentTypes = dedent(
        """
        select NAME from INCIDENT_TYPE
        """
    )

    _query_incidentTypesNotHidden = dedent(
        """
        select NAME from INCIDENT_TYPE where HIDDEN = 0
        """
    )


    def createIncidentType(self, incidentType, hidden=False):
        """
        Create the given incident type.
        """
        try:
            with self._db as db:
                db.execute(
                    self._query_createIncidentType, (incidentType, hidden)
                )
        except SQLiteError as e:
            self.log.critical(
                "Unable to create incident type: {incidentType}",
                incidentType=incidentType
            )
            raise StorageError(e)

    _query_createIncidentType = dedent(
        """
        insert or ignore into INCIDENT_TYPE (NAME, HIDDEN) values (?, ?)
        """
    )


    def showIncidentTypes(self, incidentTypes):
        """
        Show the given incident types.
        """
        return self._hideShowIncidentTypes(incidentTypes, False)


    def hideIncidentTypes(self, incidentTypes):
        """
        Hide the given incident types.
        """
        return self._hideShowIncidentTypes(incidentTypes, True)


    def _hideShowIncidentTypes(self, incidentTypes, hidden):
        """
        Show the given incident types.
        """
        try:
            with self._db as db:
                for incidentType in incidentTypes:
                    db.execute(
                        self._query_hideShowIncidentType, (hidden, incidentType)
                    )
        except SQLiteError as e:
            self.log.critical(
                "Unable to create show types: {incidentTypes}",
                incidentTypes=incidentTypes
            )
            raise StorageError(e)


    _query_hideShowIncidentType = dedent(
        """
        update INCIDENT_TYPE set HIDDEN = ? where NAME = ?
        """
    )


    def incident(self, event, number):
        """
        Look up the incident with the given number in the given event.
        """
        try:
            # Fetch incident row
            (
                version, createdTimestamp, priority, stateName,
                summary,
                locationName,
                locationConcentric,
                locationRadialHour,
                locationRadialMinute,
                locationDescription,
            ) = self._db.execute(
                self._query_incident, (event, number)
            ).fetchone()

            # Convert created timestamp to a datetime
            created = fromTimeStamp(createdTimestamp)

            # Turn state ID string into the corresponding constant
            state = IncidentState.lookupByName(stateName)

            # Look up Rangers from join table
            rangers = (
                Ranger(handle=row["RANGER_HANDLE"], name=None, status=None)
                for row in self._db.execute(
                    self._query_incident_rangers, (event, number)
                )
            )

            # Look up incident types from join table
            incidentTypes = (
                row["NAME"] for row in self._db.execute(
                    self._query_incident_types, (event, number)
                )
            )

            # Look up report entries from join table
            reportEntries = []

            for author, text, entryTimeStamp, generated in self._db.execute(
                self._query_incident_reportEntries, (event, number)
            ):
                reportEntries.append(
                    ReportEntry(
                        author=author,
                        text=text,
                        created=fromTimeStamp(entryTimeStamp),
                        system_entry=generated,
                    )
                )

        except SQLiteError as e:
            self.log.critical(
                "Unable to look up incident: {event}:{number}",
                event=event, number=number
            )
            raise StorageError(e)

        location = Location(
            name=locationName,
            address=RodGarettAddress(
                concentric=locationConcentric,
                radialHour=locationRadialHour,
                radialMinute=locationRadialMinute,
                description=locationDescription,
            ),
        )

        incident = Incident(
            number=number,
            priority=priority,
            summary=summary,
            location=location,
            rangers=rangers,
            incidentTypes=incidentTypes,
            reportEntries=reportEntries,
            created=created,
            state=state,
            version=version,
        )
        # Check for issues in stored data; disable if performance an issue
        try:
            incident.validate()
        except InvalidDataError as e:
            self.log.critical(
                "Invalid incident ({error}): {incident!r}",
                incident=incident, error=e
            )
            raise

        return incident

    _query_incident = _query(
        """
        select
            VERSION, CREATED, PRIORITY, STATE, SUMMARY,
            LOCATION_NAME,
            LOCATION_CONCENTRIC,
            LOCATION_RADIAL_HOUR,
            LOCATION_RADIAL_MINUTE,
            LOCATION_DESCRIPTION
        from INCIDENT where EVENT = ({query_eventID}) and NUMBER = ?
        """
    )

    _query_incident_rangers = _query(
        """
        select RANGER_HANDLE from INCIDENT__RANGER
        where EVENT = ({query_eventID}) and INCIDENT_NUMBER = ?
        """
    )

    _query_incident_types = _query(
        """
        select NAME from INCIDENT_TYPE where ID in (
            select INCIDENT_TYPE from INCIDENT__INCIDENT_TYPE
            where EVENT = ({query_eventID}) and INCIDENT_NUMBER = ?
        )
        """
    )

    _query_incident_reportEntries = _query(
        """
        select AUTHOR, TEXT, CREATED, GENERATED from REPORT_ENTRY
        where ID in (
            select REPORT_ENTRY from INCIDENT__REPORT_ENTRY
            where EVENT = ({query_eventID}) and INCIDENT_NUMBER = ?
        )
        """
    )


    def _incidentNumbers(self, event):
        """
        Look up all incident numbers for the given event.
        """
        try:
            for row in self._db.execute(self._query_incidentNumbers, (event,)):
                yield row["NUMBER"]
        except SQLiteError as e:
            self.log.critical(
                "Unable to look up incident numbers for event: {event}",
                event=event
            )
            raise StorageError(e)

    _query_incidentNumbers = _query(
        """
        select NUMBER from INCIDENT where EVENT = ({query_eventID})
        """
    )


    def incidents(self, event):
        """
        Look up all incidents for the given event.
        """
        for number in self._incidentNumbers(event):
            yield self.incident(event, number)


    def importIncident(self, event, incident):
        """
        Import the given incident into the given event.
        The incident number is specified by the given incident, as this is used
        to import data from an another data store.
        """
        incident.validate()

        self._addIncident(event, incident, self._importIncident)


    def createIncident(self, event, incident):
        """
        Create a new incident and add it into the given event.
        The incident number is determined by the database and must not be
        specified by the given incident.
        """
        incident.validate(noneNumber=True)

        # FIXME:STORE Add system report entry

        self._addIncident(event, incident, self._createIncident)


    def _addIncident(self, event, incident, addMethod):
        try:
            with self._db as db:
                cursor = db.cursor()
                try:
                    # Write incident row
                    addMethod(event, incident, cursor)

                    # Join with Ranger handles
                    if incident.rangers is not None:
                        for ranger in incident.rangers:
                            self._attachRanger(
                                event, incident.number, ranger.handle, cursor
                            )

                    # Join with incident types
                    if incident.incidentTypes is not None:
                        for incidentType in incident.incidentTypes:
                            self._attachIncidentType(
                                event, incident.number, incidentType, cursor
                            )

                    if incident.reportEntries is not None:
                        for reportEntry in incident.reportEntries:
                            self._addAndAttachReportEntry(
                                event, incident.number, reportEntry, cursor
                            )

                finally:
                    cursor.close()

        except SQLiteError as e:
            self.log.critical(
                "Unable to add incident to event {event}: {incident!r}",
                incident=incident, event=event
            )
            raise StorageError(e)


    @staticmethod
    def _coerceLocation(location):
        # Make sure location name and address are not None.
        # Coerce all location addresses into Rod Garett form.

        if location is None:
            locationName = None
            address = RodGarettAddress()
        else:
            locationName = location.name
            if location.address is None:
                address = RodGarettAddress()
            else:
                address = location.address.asRodGarettAddress()

        return (locationName, address)


    def _importIncident(self, event, incident, cursor):
        """
        Import the given incident to the given event.
        The incident number is specified by the given incident, as this is used
        to import data from an another data store.
        This does not attach relational data such as Rangers, incident types,
        and report entries.
        """
        locationName, address = self._coerceLocation(incident.location)

        cursor.execute(
            self._query_importIncident, (
                event,
                incident.number,
                1,  # Version is 1 because it's a new row
                asTimeStamp(incident.created),
                incident.priority,
                incident.state.name,
                incident.summary,
                locationName,
                address.concentric,
                address.radialHour,
                address.radialMinute,
                address.description,
            )
        )

    _query_importIncident = _query(
        """
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
        values (({query_eventID}), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
    )


    def _nextIncidentNumber(self, event, cursor):
        """
        Look up the next available incident number.
        """
        cursor.execute(self._query_maxIncidentNumber, (event,))
        number = cursor.fetchone()[0]
        if number is None:
            return 1
        else:
            return number + 1

    _query_maxIncidentNumber = _query(
        """
        select max(NUMBER) from INCIDENT where EVENT = ({query_eventID})
        """
    )


    def _createIncident(self, event, incident, cursor):
        """
        Add the given incident to the given event.
        The incident number is determined by the database.
        This does not attach relational data such as Rangers, incident types,
        and report entries.
        """
        assert incident.number is None
        incident.number = self._nextIncidentNumber(event, cursor)
        self._importIncident(event, incident, cursor)


    def _attachRanger(self, event, number, rangerHandle, cursor):
        """
        Attach the given Ranger to the incident with the given number in the
        given event.
        """
        cursor.execute(self._query_attachRanger, (event, number, rangerHandle))

    _query_attachRanger = _query(
        """
        insert into INCIDENT__RANGER (
            EVENT, INCIDENT_NUMBER, RANGER_HANDLE
        )
        values (({query_eventID}), ?, ?)
        """
    )


    def _attachIncidentType(self, event, number, incidentType, cursor):
        """
        Attach the given incident type to the incident with the given number in
        the given event.
        """
        cursor.execute(
            self._query_attachIncidentType, (event, number, incidentType)
        )

    _query_attachIncidentType = _query(
        """
        insert into INCIDENT__INCIDENT_TYPE (
            EVENT, INCIDENT_NUMBER, INCIDENT_TYPE
        )
        values (
            ({query_eventID}),
            ?,
            (select ID from INCIDENT_TYPE where NAME=?)
        )
        """
    )


    def _createReportEntry(self, reportEntry, cursor):
        cursor.execute(
            self._query_addReportEntry,
            (
                reportEntry.author,
                reportEntry.text,
                asTimeStamp(reportEntry.created),
                reportEntry.system_entry,
            )
        )

    _query_addReportEntry = _query(
        """
        insert into REPORT_ENTRY (AUTHOR, TEXT, CREATED, GENERATED)
        values (?, ?, ?, ?)
        """
    )


    def _addAndAttachReportEntry(self, event, number, reportEntry, cursor):
        """
        Attach the given report entry to the incident with the given number in
        the given event.
        """
        self._createReportEntry(reportEntry, cursor)
        # Join to incident
        cursor.execute(
            self._query_attachReportEntryToIncident,
            (event, number, cursor.lastrowid)
        )

    _query_attachReportEntryToIncident = _query(
        """
        insert into INCIDENT__REPORT_ENTRY (
            EVENT, INCIDENT_NUMBER, REPORT_ENTRY
        )
        values (({query_eventID}), ?, ?)
        """
    )


    def _setIncidentColumn(self, query, event, number, column, value):
        try:
            with self._db as db:
                db.execute(query, (value, event, number))
        except SQLiteError as e:
            self.log.critical(
                "Unable to set {column} for incident {event}:{number} to "
                "{value}",
                event=event, number=number, column=column, value=value
            )
            raise StorageError(e)

    _querySetIncidentColumn = _query(
        """
        update INCIDENT set {{column}} = ?
        where EVENT = ({query_eventID}) and NUMBER = ?
        """
    )


    def setIncidentPriority(self, event, number, priority):
        """
        Set the priority for the given incident in the given event.
        """
        if (type(priority) is not int or priority < 1 or priority > 5):
            raise InvalidDataError(
                "Invalid incident priority: {!r}".format(priority)
            )

        self._setIncidentColumn(
            self._query_setIncidentPriority,
            event, number, "priority", priority
        )

    _query_setIncidentPriority = _querySetIncidentColumn.format(
        column="PRIORITY"
    )


    def setIncidentState(self, event, number, state):
        """
        Set the state for the given incident in the given event.
        """
        if state not in IncidentState.iterconstants():
            raise InvalidDataError(
                "Invalid incident state: {!r}".format(state)
            )

        self._setIncidentColumn(
            self._query_setIncidentState,
            event, number, "state", state.name
        )

    _query_setIncidentState = _querySetIncidentColumn.format(
        column="STATE"
    )


    def setIncidentSummary(self, event, number, summary):
        """
        Set the summary for the given incident in the given event.
        """
        if summary is not None and type(summary) is not unicode:
            raise InvalidDataError(
                "Invalid incident summary: {!r}".format(summary)
            )

        self._setIncidentColumn(
            self._query_setIncidentSummary,
            event, number, "summary", summary
        )

    _query_setIncidentSummary = _querySetIncidentColumn.format(
        column="SUMMARY"
    )


    def setIncidentLocationName(self, event, number, name):
        """
        Set the location name for the given incident in the given event.
        """
        if name is not None and type(name) is not unicode:
            raise InvalidDataError(
                "Invalid incident location name: {!r}".format(name)
            )

        self._setIncidentColumn(
            self._query_setIncidentLocationName,
            event, number, "location name", name
        )

    _query_setIncidentLocationName = _querySetIncidentColumn.format(
        column="LOCATION_NAME"
    )


    def setIncidentLocationConcentricStreet(self, event, number, streetID):
        """
        Set the location concentric street for the given incident in the given
        event.
        """
        if streetID is not None and type(streetID) is not int:
            raise InvalidDataError(
                "Invalid incident location concentric street: {!r}"
                .format(streetID)
            )

        self._setIncidentColumn(
            self._query_setIncidentLocationConcentricStreet,
            event, number, "location concentric street", streetID
        )

    _query_setIncidentLocationConcentricStreet = _querySetIncidentColumn.format(
        column="LOCATION_CONCENTRIC"
    )


    def setIncidentLocationRadialHour(self, event, number, hour):
        """
        Set the location radial hour for the given incident in the given event.
        """
        if (
            hour is not None and
            (type(hour) is not int or hour < 1 or hour > 12)
        ):
            raise InvalidDataError(
                "Invalid incident location radial hour: {!r}".format(hour)
            )

        self._setIncidentColumn(
            self._query_setIncidentLocationRadialHour,
            event, number, "location radial hour", hour
        )

    _query_setIncidentLocationRadialHour = _querySetIncidentColumn.format(
        column="LOCATION_RADIAL_HOUR"
    )


    def setIncidentLocationRadialMinute(self, event, number, minute):
        """
        Set the location radial minute for the given incident in the given
        event.
        """
        if (
            minute is not None and
            (type(minute) is not int or minute < 0 or minute >= 60)
        ):
            raise InvalidDataError(
                "Invalid incident location radial minute: {!r}".format(minute)
            )

        self._setIncidentColumn(
            self._query_setIncidentLocationRadialMinute,
            event, number, "location radial minute", minute
        )

    _query_setIncidentLocationRadialMinute = _querySetIncidentColumn.format(
        column="LOCATION_RADIAL_MINUTE"
    )


    def setIncidentLocationDescription(self, event, number, description):
        """
        Set the location description for the given incident in the given event.
        """
        if description is not None and type(description) is not unicode:
            raise InvalidDataError(
                "Invalid incident location description: {!r}"
                .format(description)
            )

        self._setIncidentColumn(
            self._query_setIncidentLocationDescription,
            event, number, "location description", description
        )

    _query_setIncidentLocationDescription = _querySetIncidentColumn.format(
        column="LOCATION_DESCRIPTION"
    )


    def setIncidentRangers(self, event, number, rangerHandles):
        """
        Set the rangers attached to the given incident in the given event.
        """
        rangerHandles = tuple(rangerHandles)
        try:
            with self._db as db:
                cursor = db.cursor()
                try:
                    cursor.execute(
                        self._query_clearIncidentRangers, (event, number)
                    )
                    for handle in rangerHandles:
                        if type(handle) is not unicode:
                            raise InvalidDataError(
                                "Invalid Ranger handle: {!r}".format(handle)
                            )
                        self._attachRanger(event, number, handle, cursor)
                finally:
                    cursor.close()
        except SQLiteError as e:
            self.log.critical(
                "Unable to set Rangers for incident {event}:{number} to "
                "{handles}",
                event=event, number=number, handles=rangerHandles
            )
            raise StorageError(e)

    _query_clearIncidentRangers = _query(
        """
        delete from INCIDENT__RANGER
        where EVENT = ({query_eventID}) and INCIDENT_NUMBER = ?
        """
    )


    def setIncidentTypes(self, event, number, incidentTypes):
        """
        Set the incident types attached to the given incident in the given
        event.
        """
        incidentTypes = tuple(incidentTypes)
        try:
            with self._db as db:
                cursor = db.cursor()
                try:
                    cursor.execute(
                        self._query_clearIncidentTypes, (event, number)
                    )
                    for incidentType in incidentTypes:
                        if type(incidentType) is not unicode:
                            raise InvalidDataError(
                                "Invalid incident type: {!r}"
                                .format(incidentType)
                            )
                        self._attachIncidentType(
                            event, number, incidentType, cursor
                        )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self.log.critical(
                "Unable to set incident types for incident {event}:{number} to "
                "{incidentTypes}",
                event=event, number=number, incidentTypes=incidentTypes
            )
            raise StorageError(e)

    _query_clearIncidentTypes = _query(
        """
        delete from INCIDENT__INCIDENT_TYPE
        where EVENT = ({query_eventID}) and INCIDENT_NUMBER = ?
        """
    )


    def addIncidentReportEntry(self, event, number, reportEntry):
        """
        Add a report entry to the incident with the given number in the given
        event.
        """
        reportEntry.validate()
        try:
            with self._db as db:
                cursor = db.cursor()
                try:
                    self._addAndAttachReportEntry(
                        event, number, reportEntry, cursor
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self.log.critical(
                "Unable to add report entry for incident {event}:{number}: "
                "{reportEntry}",
                event=event, number=number, reportEntry=reportEntry
            )
            raise StorageError(e)


    def createIncidentReport(self, incidentReport):
        """
        Create a new incident report.
        The incident report ID is determined by the database and must not be
        specified by the given incident report.
        """
        incidentReport.validate(noneID=True)

        assert incidentReport.number is None

        try:
            with self._db as db:
                cursor = db.cursor()
                try:
                    cursor.execute(
                        self._query_createIncidentReport, (
                            incidentReport.number, incidentReport.created
                        )
                    )
                    incidentReport.number = cursor.lastrowid
                finally:
                    cursor.close()

        except SQLiteError as e:
            self.log.critical(
                "Unable to create incident report: {incidentReport!r}",
                incidentReport=incidentReport
            )
            raise StorageError(e)

    _query_createIncidentReport = _query(
        """
        insert into INCIDENT_REPORT (NUMBER, CREATED) values (?, ?)
        """
    )


    def addIncidentReportReportEntry(self, id, reportEntry):
        """
        Add a report entry to the incident report with the given id in the given
        event.
        """
        reportEntry.validate()
        try:
            with self._db as db:
                cursor = db.cursor()
                try:
                    self._createReportEntry(reportEntry, cursor)
                    # Join to incident report
                    cursor.execute(
                        self._query_attachReportEntryToIncidentReport,
                        (id, cursor.lastrowid)
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self.log.critical(
                "Unable to add report entry for incident report {id}: "
                "{reportEntry}",
                id=id, reportEntry=reportEntry
            )
            raise StorageError(e)

    _query_attachReportEntryToIncidentReport = _query(
        """
        insert into INCIDENT_REPORT__REPORT_ENTRY (
            INCIDENT_REPORT_NUMBER, REPORT_ENTRY
        )
        values (?, ?)
        """
    )


    def concentricStreetsByID(self, event):
        """
        Look up all concentric street names, indexed by ID, IDs for the given
        event.
        """
        result = {}

        try:
            for streetID, streetName in (
                self._db.execute(self._query_concentricStreets, (event,))
            ):
                result[streetID] = streetName
        except SQLiteError as e:
            self.log.critical(
                "Unable to look up concentric street names for event: {event}",
                event=event
            )
            raise StorageError(e)

        return result

    _query_concentricStreets = _query(
        """
        select ID, NAME from CONCENTRIC_STREET
        where EVENT = ({query_eventID})
        """
    )


    def createConcentricStreet(self, event, id, name):
        """
        Create the given concentric street name and ID into the given event.
        """
        try:
            with self._db as db:
                db.execute(
                    self._query_addConcentricStreet, (event, id, name)
                )
        except SQLiteError as e:
            self.log.critical(
                "Unable to concentric street to event {event}: ({id}){name}",
                event=event, id=id, name=name
            )
            raise StorageError(e)

    _query_addConcentricStreet = _query(
        """
        insert into CONCENTRIC_STREET (EVENT, ID, NAME)
        values (({query_eventID}), ?, ?)
        """
    )


    def _eventAccess(self, event, mode):
        try:
            for row in self._db.execute(
                self._query_eventAccess, (event, mode)
            ):
                yield row["EXPRESSION"]
        except SQLiteError as e:
            self.log.critical(
                "Unable to look up {mode} access for event: {event}",
                event=event, mode=mode
            )
            raise StorageError(e)

    _query_eventAccess = _query(
        """
        select EXPRESSION from EVENT_ACCESS
        where EVENT = ({query_eventID}) and MODE = ?
        """
    )


    def _setEventAccess(self, event, mode, expressions):
        try:
            with self._db as db:
                cursor = db.cursor()
                try:
                    self.log.info(
                        "Clearing access: {event} {mode}",
                        event=event, mode=mode
                    )
                    cursor.execute(self._query_clearEventAccess, (event, mode))
                    for expression in frozenset(expressions):
                        self.log.info(
                            "Adding access: {event} {mode} {expression}",
                            event=event, mode=mode, expression=expression
                        )
                        cursor.execute(
                            self._query_addEventAccess,
                            (event, expression, mode)
                        )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self.log.critical(
                "Unable to set {mode} access for event: {event}",
                event=event, mode=mode, expressions=expressions
            )
            raise StorageError(e)

    _query_clearEventAccess = _query(
        """
        delete from EVENT_ACCESS
        where EVENT = ({query_eventID}) and MODE = ?
        """
    )

    _query_addEventAccess = _query(
        """
        insert into EVENT_ACCESS (EVENT, EXPRESSION, MODE)
        values (({query_eventID}), ?, ?)
        """
    )


    def readers(self, event):
        """
        Look up the allowed readers for the given event.
        """
        return self._eventAccess(event, "read")


    def setReaders(self, event, readers):
        """
        Set the allowed readers for the given event.
        """
        return self._setEventAccess(event, "read", readers)


    def writers(self, event):
        """
        Look up the allowed writers for the given event.
        """
        return self._eventAccess(event, "write")


    def setWriters(self, event, writers):
        """
        Set the allowed writers for the given event.
        """
        return self._setEventAccess(event, "write", writers)


    def explainQueryPlans(self):
        queries = [
            (getattr(self, k), k[7:])
            for k in sorted(vars(self.__class__))
            if k.startswith("_query_")
        ]

        for query, name in queries:
            try:
                lines = (
                    QueryPlanExplanation.Line(
                        nestingOrder, selectFrom, details
                    )
                    for n, nestingOrder, selectFrom, details in (
                        self._db.execute(
                            "explain query plan {}".format(query),
                            ("1",) * query.count("?")  # Dummy args list
                        )
                    )
                )
            except OperationalError as e:
                lines = (
                    QueryPlanExplanation.Line(
                        None, None, "{}".format(e),
                    ),
                )

            yield QueryPlanExplanation(name, query, lines)



class Row(LameRow):
    def get(self, key, default=None):
        if key in self.keys():
            return self[key]
        else:
            return default



def loadSchema():
    fp = FilePath(__file__).parent().child("schema.sqlite")
    return fp.getContent().decode("utf-8")


def configure(db):
    db.row_factory = Row

    return db


def dbForFilePath(filePath):
    if filePath is None:
        fileName = u":memory:"
    else:
        fileName = filePath.path

    return configure(connect(fileName))


def createDB(filePath=None):
    schema = loadSchema()

    db = dbForFilePath(filePath)
    db.executescript(schema)
    db.commit()

    return configure(db)


def openDB(filePath=None, create=False):
    """
    Open an SQLite DB with the schema for this application.
    """
    if filePath is not None and filePath.exists():
        return dbForFilePath(filePath)

    if create:
        return createDB(filePath)

    raise RuntimeError("Database does not exist")


def printSchema(db):
    for (tableName,) in db.execute(
        """
        select NAME from SQLITE_MASTER where TYPE='table' order by NAME;
        """
    ):
        print("{}:".format(tableName))
        for (
            rowNumber, columnName, columnType,
            columnNotNull, columnDefault, columnPK,
        ) in db.execute("pragma table_info('{}');".format(tableName)):
            print("  {n}: {name}({type}){null}{default}{pk}".format(
                n=rowNumber,
                name=columnName,
                type=columnType,
                null=" not null" if columnNotNull else "",
                default=" [{}]".format(columnDefault) if columnDefault else "",
                pk=" *{}".format(columnPK) if columnPK else "",
            ))



class QueryPlanExplanation(object):
    class Line(object):
        def __init__(self, nestingOrder, selectFrom, details):
            self.nestingOrder = nestingOrder
            self.selectFrom   = selectFrom
            self.details      = details


        def asText(self):
            return u"[{},{}] {}".format(
                self.nestingOrder, self.selectFrom, self.details
            )


    def __init__(self, name, query, lines):
        self.name  = name
        self.query = query
        self.lines = tuple(lines)


    def __str__(self):
        return str(self.asText())


    def asText(self):
        text = [u"{}:".format(self.name), u"", u"  -- query --", u""]

        text.extend(
            u"    {}".format(l)
            for l in self.query.strip().split("\n")
        )

        if self.lines:
            text.extend((u"", "  -- query plan --", u""))
            text.extend(u"    {}".format(l.asText()) for l in self.lines)

        return u"\n".join(text)



zeroTimeDelta = TimeDelta(0)


def asTimeStamp(datetime):
    assert datetime.tzinfo is not None, repr(datetime)
    assert datetime.tzinfo.utcoffset(datetime) == zeroTimeDelta

    return timegm(datetime.timetuple())


def fromTimeStamp(timestamp):
    return DateTime.fromtimestamp(timestamp, tz=utc)
