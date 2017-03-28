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

from twisted.python.constants import NamedConstant
from twisted.python.filepath import FilePath
from twisted.logger import Logger

from ..tz import utc, utcNow
from ..data.json import objectFromJSONBytesIO, incidentFromJSON
from ..data.model import (
    Event, IncidentType, Incident, IncidentState,
    Ranger, ReportEntry, Location, RodGarettAddress,
    IncidentReport, InvalidDataError,
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
        for eventID in multiStore:
            event = Event(eventID)

            self.log.info("Creating event: {event}", event=event)
            self.createEvent(event)

            eventStore = multiStore[event.id]

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


    def loadFromEventJSON(self, event, filePath, trialRun=False):
        """
        Load event data from a file containing JSON.
        """
        assert type(event) is Event

        with filePath.open() as fileHandle:
            eventJSON = objectFromJSONBytesIO(fileHandle)

            self.log.info("Creating event: {event}", event=event)
            self.createEvent(event)

            # Load incidents
            for incidentJSON in eventJSON:
                number = incidentJSON["number"]

                if type(number) is not int or number < 1:
                    raise InvalidDataError(
                        "Invalid incident number: {}".format(number)
                    )

                try:
                    incident = incidentFromJSON(incidentJSON, number)
                    incident.validate()
                except InvalidDataError as e:
                    if trialRun:
                        self.log.critical(
                            "Unable to load incident #{number}: {error}",
                            number=number, error=e,
                        )
                    else:
                        raise

                for incidentType in incident.incidentTypes:
                    self.createIncidentType(incidentType, hidden=True)

                self.log.info(
                    "Creating incident in {event}: {incident}",
                    event=event, incident=incident
                )
                if not trialRun:
                    self.importIncident(event, incident)


    def events(self):
        """
        Look up all events in this store.
        """
        try:
            for row in self._db.execute(self._query_events):
                yield Event(row["name"])
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
        assert type(event) is Event
        event.validate()

        try:
            with self._db as db:
                db.execute(self._query_createEvent, (event.id,))
        except SQLiteError as e:
            self.log.critical("Unable to create event: {event}", event=event)
            raise StorageError(e)

        self.log.info(
            "Created event: {event}", storeWriteClass=Event, event=event,
        )

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
        assert type(incidentType) is str

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

        self.log.info(
            "Created incident type: {incidentType} (hidden={hidden})",
            storeWriteClass=IncidentType,
            incidentType=incidentType, hidden=hidden,
        )

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
        Hide or show the given incident types.
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

        self.log.info(
            "Setting hidden to {hidden} for incident types: {incidentTypes}",
            storeWriteClass=IncidentType,
            incidentTypes=incidentTypes, hidden=hidden,
        )

    _query_hideShowIncidentType = dedent(
        """
        update INCIDENT_TYPE set HIDDEN = ? where NAME = ?
        """
    )


    def incident(self, event, number):
        """
        Look up the incident with the given number in the given event.
        """
        assert type(event) is Event

        try:
            # Fetch incident row
            cursor = self._db.execute(self._query_incident, (event.id, number))
            (
                version, createdTimestamp, priority, stateName,
                summary,
                locationName,
                locationConcentric,
                locationRadialHour,
                locationRadialMinute,
                locationDescription,
            ) = cursor.fetchone()

            # Convert created timestamp to a datetime
            created = fromTimeStamp(createdTimestamp)

            # Turn state ID string into the corresponding constant
            state = IncidentState.lookupByName(stateName)

            # Look up Rangers from join table
            rangers = (
                Ranger(handle=row["RANGER_HANDLE"], name=None, status=None)
                for row in self._db.execute(
                    self._query_incident_rangers, (event.id, number)
                )
            )

            # Look up incident types from join table
            incidentTypes = (
                row["NAME"] for row in self._db.execute(
                    self._query_incident_types, (event.id, number)
                )
            )

            # Look up report entries from join table
            reportEntries = []

            for author, text, entryTimeStamp, generated in self._db.execute(
                self._query_incident_reportEntries, (event.id, number)
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
                "Unable to look up incident: {event}#{number}",
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
        # Check for issues in stored data
        try:
            incident.validate()
        except InvalidDataError as e:
            self.log.critical(
                "Invalid stored incident ({error}): {incident!r}",
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
        assert type(event) is Event

        try:
            for row in self._db.execute(
                self._query_incidentNumbers, (event.id,)
            ):
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
        assert type(event) is Event

        for number in self._incidentNumbers(event):
            yield self.incident(event, number)


    def importIncident(self, event, incident):
        """
        Import the given incident into the given event.
        The incident number is specified by the given incident, as this is used
        to import data from an another data store.
        """
        assert type(event) is Event
        incident.validate()

        try:
            with self._db as db:
                cursor = db.cursor()
                try:
                    self._addIncident(
                        event, incident, self._importIncident, cursor
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self.log.critical(
                "Unable to import incident to event {event}: {incident!r}",
                incident=incident, event=event
            )
            raise StorageError(e)


    def createIncident(self, event, incident, author):
        """
        Create a new incident and add it into the given event.
        The incident number is determined by the database and must not be
        specified by the given incident.
        """
        assert type(event) is Event
        incident.validate(noneNumber=True)

        # FIXME:STORE Add system report entry

        try:
            with self._db as db:
                cursor = db.cursor()
                try:
                    self._addIncident(
                        event, incident, self._createIncident, cursor
                    )
                    self._addInitialReportEntry(event, incident, author, cursor)
                finally:
                    cursor.close()
        except SQLiteError as e:
            self.log.critical(
                "Unable to create incident in event {event}: {incident!r}",
                incident=incident, event=event
            )
            raise StorageError(e)


    def _addIncident(self, event, incident, addMethod, cursor):
        assert type(event) is Event

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
                self._addAndAttachReportEntryToIncident(
                    event, incident.number, reportEntry, cursor
                )


    def _addInitialReportEntry(self, event, incident, author, cursor):
        assert type(event) is Event

        now = utcNow()

        def addEntry(label, value):
            if value:
                if isinstance(value, NamedConstant):
                    value = value.name

                systemEntry = ReportEntry(
                    text="Changed {} to: {}".format(label, value),
                    author=author, created=now, system_entry=True,
                )
                self._addAndAttachReportEntryToIncident(
                    event, incident.number, systemEntry, cursor
                )


        if incident.priority != 3:
            addEntry("priority", incident.priority)

        if incident.state != IncidentState.new:
            addEntry("state", incident.state)

        addEntry("summary", incident.summary)

        location = incident.location
        if location:
            addEntry("location name", location.name)

            address = location.address
            if address:
                addEntry("location description", address.description)

                if isinstance(address, RodGarettAddress):
                    addEntry("location concentric street", address.concentric)
                    addEntry("location radial hour", address.radialHour)
                    addEntry("location radial minute", address.radialMinute)

        if incident.rangers:
            handles = (ranger.handle for ranger in incident.rangers)
            addEntry("Rangers", ", ".join(handles))

        if incident.incidentTypes:
            addEntry("incident types", ", ".join(incident.incidentTypes))


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
        event.validate()

        locationName, address = self._coerceLocation(incident.location)

        cursor.execute(
            self._query_importIncident, (
                event.id,
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

        self.log.info(
            "Created incident {event}:{incident}",
            storeWriteClass=Incident, event=event, incident=incident,
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
        assert type(event) is Event

        cursor.execute(self._query_maxIncidentNumber, (event.id,))
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
        assert type(event) is Event
        assert incident.number is None
        incident.number = self._nextIncidentNumber(event, cursor)
        self._importIncident(event, incident, cursor)


    def _attachRanger(self, event, number, rangerHandle, cursor):
        """
        Attach the given Ranger to the incident with the given number in the
        given event.
        """
        event.validate()

        cursor.execute(
            self._query_attachRanger, (event.id, number, rangerHandle)
        )

        self.log.info(
            "Attached Ranger {rangerHandle} to incident "
            "{event}#{incidentNumber}",
            storeWriteClass=Incident,
            event=event, incidentNumber=number, rangerHandle=rangerHandle,
        )

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
        event.validate()

        cursor.execute(
            self._query_attachIncidentType, (event.id, number, incidentType)
        )

        self.log.info(
            "Attached incident type {incidentType} to incident "
            "{event}#{incidentNumber}",
            storeWriteClass=Incident,
            event=event, incidentNumber=number, incidentType=incidentType,
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

        self.log.info(
            "Created report entry: {reportEntry}",
            storeWriteClass=ReportEntry, reportEntry=reportEntry,
        )

    _query_addReportEntry = _query(
        """
        insert into REPORT_ENTRY (AUTHOR, TEXT, CREATED, GENERATED)
        values (?, ?, ?, ?)
        """
    )


    def _addAndAttachReportEntryToIncident(
        self, event, number, reportEntry, cursor
    ):
        """
        Attach the given report entry to the incident with the given number in
        the given event.
        """
        event.validate()

        self._createReportEntry(reportEntry, cursor)
        # Join to incident
        cursor.execute(
            self._query_attachReportEntryToIncident,
            (event.id, number, cursor.lastrowid)
        )

        self.log.info(
            "Attached report entry to incident {event}#{incidentNumber}: "
            "{reportEntry}",
            storeWriteClass=Incident,
            event=event, incidentNumber=number, reportEntry=reportEntry,
        )

    _query_attachReportEntryToIncident = _query(
        """
        insert into INCIDENT__REPORT_ENTRY (
            EVENT, INCIDENT_NUMBER, REPORT_ENTRY
        )
        values (({query_eventID}), ?, ?)
        """
    )


    def _setIncidentColumn(self, query, event, number, column, value, author):
        event.validate()

        systemEntry = ReportEntry(
            text="Changed {} to: {}".format(column, value),
            author=author, created=utcNow(), system_entry=True,
        )

        try:
            with self._db as db:
                cursor = db.cursor()
                try:
                    cursor.execute(query, (value, event.id, number))
                    self._addAndAttachReportEntryToIncident(
                        event, number, systemEntry, cursor
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self.log.critical(
                "Author {author} unable to set {column} for incident "
                "{event}#{number} to {value}",
                event=event, number=number,
                column=column, value=value, author=author,
            )
            raise StorageError(e)

        self.log.info(
            "{author} updated incident {event}#{incidentNumber}: "
            "{column}={value}",
            storeWriteClass=Incident,
            query=query,
            event=event,
            incidentNumber=number,
            column=column,
            value=value,
            author=author,
        )

    _querySetIncidentColumn = _query(
        """
        update INCIDENT set {{column}} = ?
        where EVENT = ({query_eventID}) and NUMBER = ?
        """
    )


    def setIncidentPriority(self, event, number, priority, author):
        """
        Set the priority for the given incident in the given event.
        """
        assert type(event) is Event

        if (type(priority) is not int or priority < 1 or priority > 5):
            raise InvalidDataError(
                "Invalid incident priority: {!r}".format(priority)
            )

        self._setIncidentColumn(
            self._query_setIncidentPriority,
            event, number, "priority", priority, author
        )

    _query_setIncidentPriority = _querySetIncidentColumn.format(
        column="PRIORITY"
    )


    def setIncidentState(self, event, number, state, author):
        """
        Set the state for the given incident in the given event.
        """
        assert type(event) is Event

        if state not in IncidentState.iterconstants():
            raise InvalidDataError(
                "Invalid incident state: {!r}".format(state)
            )

        self._setIncidentColumn(
            self._query_setIncidentState,
            event, number, "state", state.name, author
        )

    _query_setIncidentState = _querySetIncidentColumn.format(
        column="STATE"
    )


    def setIncidentSummary(self, event, number, summary, author):
        """
        Set the summary for the given incident in the given event.
        """
        assert type(event) is Event

        if summary is not None and type(summary) is not str:
            raise InvalidDataError(
                "Invalid incident summary: {!r}".format(summary)
            )

        self._setIncidentColumn(
            self._query_setIncidentSummary,
            event, number, "summary", summary, author
        )

    _query_setIncidentSummary = _querySetIncidentColumn.format(
        column="SUMMARY"
    )


    def setIncidentLocationName(self, event, number, name, author):
        """
        Set the location name for the given incident in the given event.
        """
        assert type(event) is Event

        if name is not None and type(name) is not str:
            raise InvalidDataError(
                "Invalid incident location name: {!r}".format(name)
            )

        self._setIncidentColumn(
            self._query_setIncidentLocationName,
            event, number, "location name", name, author
        )

    _query_setIncidentLocationName = _querySetIncidentColumn.format(
        column="LOCATION_NAME"
    )


    def setIncidentLocationConcentricStreet(
        self, event, number, streetID, author
    ):
        """
        Set the location concentric street for the given incident in the given
        event.
        """
        assert type(event) is Event

        if streetID is not None and type(streetID) is not int:
            raise InvalidDataError(
                "Invalid incident location concentric street: {!r}"
                .format(streetID)
            )

        self._setIncidentColumn(
            self._query_setIncidentLocationConcentricStreet,
            event, number, "location concentric street", streetID, author
        )

    _query_setIncidentLocationConcentricStreet = _querySetIncidentColumn.format(
        column="LOCATION_CONCENTRIC"
    )


    def setIncidentLocationRadialHour(self, event, number, hour, author):
        """
        Set the location radial hour for the given incident in the given event.
        """
        assert type(event) is Event

        if (
            hour is not None and
            (type(hour) is not int or hour < 1 or hour > 12)
        ):
            raise InvalidDataError(
                "Invalid incident location radial hour: {!r}".format(hour)
            )

        self._setIncidentColumn(
            self._query_setIncidentLocationRadialHour,
            event, number, "location radial hour", hour, author
        )

    _query_setIncidentLocationRadialHour = _querySetIncidentColumn.format(
        column="LOCATION_RADIAL_HOUR"
    )


    def setIncidentLocationRadialMinute(self, event, number, minute, author):
        """
        Set the location radial minute for the given incident in the given
        event.
        """
        assert type(event) is Event

        if (
            minute is not None and
            (type(minute) is not int or minute < 0 or minute >= 60)
        ):
            raise InvalidDataError(
                "Invalid incident location radial minute: {!r}".format(minute)
            )

        self._setIncidentColumn(
            self._query_setIncidentLocationRadialMinute,
            event, number, "location radial minute", minute, author
        )

    _query_setIncidentLocationRadialMinute = _querySetIncidentColumn.format(
        column="LOCATION_RADIAL_MINUTE"
    )


    def setIncidentLocationDescription(
        self, event, number, description, author
    ):
        """
        Set the location description for the given incident in the given event.
        """
        assert type(event) is Event

        if description is not None and type(description) is not str:
            raise InvalidDataError(
                "Invalid incident location description: {!r}"
                .format(description)
            )

        self._setIncidentColumn(
            self._query_setIncidentLocationDescription,
            event, number, "location description", description, author
        )

    _query_setIncidentLocationDescription = _querySetIncidentColumn.format(
        column="LOCATION_DESCRIPTION"
    )


    def setIncidentRangers(self, event, number, rangerHandles, author):
        """
        Set the rangers attached to the given incident in the given event.
        """
        event.validate()

        rangerHandles = tuple(rangerHandles)

        systemEntry = ReportEntry(
            text="Changed Rangers to: {}".format(", ".join(rangerHandles)),
            author=author, created=utcNow(), system_entry=True,
        )

        try:
            with self._db as db:
                cursor = db.cursor()
                try:
                    cursor.execute(
                        self._query_clearIncidentRangers, (event.id, number)
                    )
                    for handle in rangerHandles:
                        if type(handle) is not str:
                            raise InvalidDataError(
                                "Invalid Ranger handle: {!r}".format(handle)
                            )
                        self._attachRanger(event, number, handle, cursor)
                    self._addAndAttachReportEntryToIncident(
                        event, number, systemEntry, cursor
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self.log.critical(
                "Unable to set Rangers for incident {event}#{number} to "
                "{handles}",
                event=event, number=number, handles=rangerHandles
            )
            raise StorageError(e)

        self.log.info(
            "{author} set Rangers for incident {event}#{incidentNumber}: "
            "{rangerHandles}",
            storeWriteClass=Incident,
            author=author,
            event=event,
            incidentNumber=number,
            rangerHandles=rangerHandles,
        )

    _query_clearIncidentRangers = _query(
        """
        delete from INCIDENT__RANGER
        where EVENT = ({query_eventID}) and INCIDENT_NUMBER = ?
        """
    )


    def setIncidentTypes(self, event, number, incidentTypes, author):
        """
        Set the incident types attached to the given incident in the given
        event.
        """
        event.validate()

        incidentTypes = tuple(incidentTypes)

        systemEntry = ReportEntry(
            text="Changed incident types to: {}".format(
                ", ".join(incidentTypes)
            ),
            author=author, created=utcNow(), system_entry=True,
        )

        try:
            with self._db as db:
                cursor = db.cursor()
                try:
                    cursor.execute(
                        self._query_clearIncidentTypes, (event.id, number)
                    )
                    for incidentType in incidentTypes:
                        if type(incidentType) is not str:
                            raise InvalidDataError(
                                "Invalid incident type: {!r}"
                                .format(incidentType)
                            )
                        self._attachIncidentType(
                            event, number, incidentType, cursor
                        )
                    self._addAndAttachReportEntryToIncident(
                        event, number, systemEntry, cursor
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self.log.critical(
                "Unable to set incident types for incident {event}#{number} to "
                "{incidentTypes}",
                event=event, number=number, incidentTypes=incidentTypes
            )
            raise StorageError(e)

        self.log.info(
            "{author} set incident types for incident "
            "{event}#{incidentNumber}: {incidentTypes}",
            storeWriteClass=Incident,
            author=author,
            event=event,
            incidentNumber=number,
            incidentTypes=incidentTypes,
        )

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
        assert type(event) is Event

        reportEntry.validate()
        try:
            with self._db as db:
                cursor = db.cursor()
                try:
                    self._addAndAttachReportEntryToIncident(
                        event, number, reportEntry, cursor
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self.log.critical(
                "Unable to add report entry for incident {event}#{number}: "
                "{reportEntry}",
                event=event, number=number, reportEntry=reportEntry
            )
            raise StorageError(e)


    def incidentReport(self, number):
        """
        Look up the incident report with the given number.
        """
        try:
            # Fetch incident report row
            cursor = self._db.execute(self._query_incidentReport, (number,))
            createdTimestamp, summary = cursor.fetchone()

            # Convert created timestamp to a datetime
            created = fromTimeStamp(createdTimestamp)

            # Look up report entries from join table
            reportEntries = []

            for author, text, entryTimeStamp, generated in self._db.execute(
                self._query_incidentReport_reportEntries, (number,)
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
                "Unable to look up incident report: {number}", number=number
            )
            raise StorageError(e)

        incidentReport = IncidentReport(
            number=number,
            summary=summary,
            created=created,
            reportEntries=reportEntries,
        )
        # Check for issues in stored data
        try:
            incidentReport.validate()
        except InvalidDataError as e:
            self.log.critical(
                "Invalid stored incident report ({error}): {incidentReport!r}",
                incidentReport=incidentReport, error=e
            )
            raise

        return incidentReport

    _query_incidentReport = _query(
        """
        select CREATED, SUMMARY from INCIDENT_REPORT where NUMBER = ?
        """
    )

    _query_incidentReport_reportEntries = _query(
        """
        select AUTHOR, TEXT, CREATED, GENERATED from REPORT_ENTRY
        where ID in (
            select REPORT_ENTRY from INCIDENT_REPORT__REPORT_ENTRY
            where INCIDENT_REPORT_NUMBER = ?
        )
        """
    )


    def _incidentReportNumbers(self, attachedTo):
        """
        Look up all incident report numbers.
        """
        if attachedTo is not None:
            event, number = attachedTo
            if (event is None and number is None):
                sql = (self._query_unAttachedIncidentReportNumbers,)
            else:
                sql = (
                    self._query_attachedIncidentReportNumbers,
                    (event.id, number)
                )
        else:
            sql = (self._query_incidentReportNumbers,)

        try:
            for row in self._db.execute(*sql):
                yield row["NUMBER"]
        except SQLiteError as e:
            self.log.critical("Unable to look up incident report numbers")
            raise StorageError(e)

    _query_incidentReportNumbers = _query(
        """
        select NUMBER from INCIDENT_REPORT
        """
    )

    _query_unAttachedIncidentReportNumbers = _query(
        """
        select NUMBER from INCIDENT_REPORT
        where NUMBER not in (
            select INCIDENT_REPORT_NUMBER from INCIDENT_INCIDENT_REPORT
        )
        """
    )

    _query_attachedIncidentReportNumbers = _query(
        """
        select NUMBER from INCIDENT_REPORT
        where NUMBER in (
            select INCIDENT_REPORT_NUMBER from INCIDENT_INCIDENT_REPORT
            where EVENT = ({query_eventID}) and INCIDENT_NUMBER = ?
        )
        """
    )


    def incidentReports(self, attachedTo=None):
        """
        Look up all incident reports.
        """
        for number in self._incidentReportNumbers(attachedTo):
            yield self.incidentReport(number)


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
                            incidentReport.number,
                            asTimeStamp(incidentReport.created),
                            incidentReport.summary,
                        )
                    )
                    incidentReport.number = cursor.lastrowid

                    if incidentReport.reportEntries is not None:
                        for reportEntry in incidentReport.reportEntries:
                            self._addAndAttachReportEntryToIncidentReport(
                                incidentReport.number, reportEntry, cursor
                            )

                finally:
                    cursor.close()

        except SQLiteError as e:
            self.log.critical(
                "Unable to create incident report: {incidentReport!r}",
                incidentReport=incidentReport
            )
            raise StorageError(e)

        self.log.info(
            "Created incident report: {incidentReport}",
            storeWriteClass=IncidentReport, incidentReport=incidentReport,
        )

    _query_createIncidentReport = _query(
        """
        insert into INCIDENT_REPORT (NUMBER, CREATED, SUMMARY) values (?, ?, ?)
        """
    )


    def _setIncidentReportColumn(self, query, number, column, value, author):
        systemEntry = ReportEntry(
            text="Changed {} to: {}".format(column, value),
            author=author, created=utcNow(), system_entry=True,
        )

        try:
            with self._db as db:
                cursor = db.cursor()
                try:
                    cursor.execute(query, (value, number))
                    self._addAndAttachReportEntryToIncidentReport(
                        number, systemEntry, cursor
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self.log.critical(
                "Author {author} unable to set {column} for incident report "
                "{number} to {value}",
                number=number, column=column, value=value, author=author,
            )
            raise StorageError(e)

        self.log.info(
            "{author} updated incident report #{incidentReportNumber}: "
            "{column}={value}",
            storeWriteClass=IncidentReport,
            query=query,
            incidentReportNumber=number,
            column=column,
            value=value,
            author=author,
        )

    _querySetIncidentReportColumn = _query(
        """
        update INCIDENT_REPORT set {{column}} = ? where NUMBER = ?
        """
    )


    def setIncidentReportSummary(self, number, summary, author):
        """
        Set the summary for the incident report with the given number.
        """
        if summary is not None and type(summary) is not str:
            raise InvalidDataError(
                "Invalid incident report summary: {!r}".format(summary)
            )

        self._setIncidentReportColumn(
            self._query_setIncidentReportSummary,
            number, "summary", summary, author
        )

    _query_setIncidentReportSummary = _querySetIncidentReportColumn.format(
        column="SUMMARY"
    )


    def addIncidentReportReportEntry(self, number, reportEntry):
        """
        Add a report entry to the incident report with the given number.
        """
        reportEntry.validate()
        try:
            with self._db as db:
                cursor = db.cursor()
                try:
                    self._addAndAttachReportEntryToIncidentReport(
                        number, reportEntry, cursor
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self.log.critical(
                "Unable to add report entry for incident report {number}: "
                "{reportEntry}",
                number=number, reportEntry=reportEntry
            )
            raise StorageError(e)


    def _addAndAttachReportEntryToIncidentReport(
        self, number, reportEntry, cursor
    ):
        """
        Create the given report entry and attach it to the incident report with
        the given number.
        """
        self._createReportEntry(reportEntry, cursor)
        # Join to incident report
        cursor.execute(
            self._query_attachReportEntryToIncidentReport,
            (number, cursor.lastrowid)
        )

        self.log.info(
            "Attached report entry to incident report #{incidentReportNumber}: "
            "{reportEntry}",
            storeWriteClass=Incident,
            incidentReportNumber=number, reportEntry=reportEntry,
        )

    _query_attachReportEntryToIncidentReport = _query(
        """
        insert into INCIDENT_REPORT__REPORT_ENTRY (
            INCIDENT_REPORT_NUMBER, REPORT_ENTRY
        )
        values (?, ?)
        """
    )


    def attachIncidentReportToIncident(
        self, incidentReportNumber, event, incidentNumber
    ):
        """
        Attach the incident report with the given number to the incident with
        the given number in the given event.
        """
        event.validate()

        try:
            with self._db as db:
                cursor = db.cursor()
                try:
                    cursor.execute(
                        self._query_attachIncidentReportToIncident,
                        (event.id, incidentNumber, incidentReportNumber)
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self.log.critical(
                "Unable to attach incident report {incidentReportNumber} "
                "to incident {incidentNumber}",
                incidentReportNumber=incidentReportNumber,
                incidentNumber=incidentNumber,
            )
            raise StorageError(e)

        self.log.info(
            "Attached incident report #{incidentReportNumber} to incident "
            "{event}#{incidentNumber}",
            storeWriteClass=Incident,
            incidentReportNumber=incidentReportNumber,
            event=event,
            incidentNumber=incidentNumber,
        )

    _query_attachIncidentReportToIncident = _query(
        """
        insert into INCIDENT_INCIDENT_REPORT (
            EVENT, INCIDENT_NUMBER, INCIDENT_REPORT_NUMBER
        )
        values (({query_eventID}), ?, ?)
        """
    )


    def detachIncidentReportFromIncident(
        self, incidentReportNumber, event, incidentNumber
    ):
        """
        Detach the incident report with the given number from the incident with
        the given number in the given event.
        """
        event.validate()

        try:
            with self._db as db:
                cursor = db.cursor()
                try:
                    cursor.execute(
                        self._query_detachIncidentReportFromIncident,
                        (event.id, incidentNumber, incidentReportNumber)
                    )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self.log.critical(
                "Unable to detach incident report {incidentReportNumber} "
                "to incident {incidentNumber}",
                incidentReportNumber=incidentReportNumber,
                incidentNumber=incidentNumber,
            )
            raise StorageError(e)

        self.log.info(
            "Detached incident report #{incidentReportNumber} from incident "
            "{event}#{incidentNumber}",
            storeWriteClass=Incident,
            incidentReportNumber=incidentReportNumber,
            event=event,
            incidentNumber=incidentNumber,
        )

    _query_detachIncidentReportFromIncident = _query(
        """
        delete from INCIDENT_INCIDENT_REPORT
        where
            EVENT = ({query_eventID}) and
            INCIDENT_NUMBER = ? and
            INCIDENT_REPORT_NUMBER = ?
        """
    )


    def incidentsAttachedToIncidentReport(self, incidentReportNumber):
        """
        Look up incidents attached to the incident report with the given number.
        """
        try:
            for row in self._db.execute(
                self._query_incidentsAttachedToIncidentReport,
                (incidentReportNumber,)
            ):
                yield (Event(row["EVENT"]), row["INCIDENT_NUMBER"])
        except SQLiteError as e:
            self.log.critical(
                "Unable to look up incidents attached to incident report: "
                "{incidentReportNumber}",
                incidentReportNumber=incidentReportNumber
            )
            raise StorageError(e)

    _query_incidentsAttachedToIncidentReport = _query(
        """
        select e.NAME as EVENT, iir.INCIDENT_NUMBER as INCIDENT_NUMBER
        from INCIDENT_INCIDENT_REPORT iir
        join EVENT e on e.ID = iir.EVENT
        where iir.INCIDENT_REPORT_NUMBER = ?
        """
    )


    def concentricStreetsByID(self, event):
        """
        Look up all concentric street names, indexed by ID, IDs for the given
        event.
        """
        assert type(event) is Event

        result = {}

        try:
            for streetID, streetName in (
                self._db.execute(self._query_concentricStreets, (event.id,))
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
        event.validate()

        try:
            with self._db as db:
                db.execute(
                    self._query_addConcentricStreet, (event.id, id, name)
                )
        except SQLiteError as e:
            self.log.critical(
                "Unable to concentric street to event {event}: ({id}){name}",
                event=event, id=id, name=name
            )
            raise StorageError(e)

        self.log.info(
            "Created concentric street in {event}: {streetName}",
            storeWriteClass=Event, event=event, concentricStreetName=name,
        )

    _query_addConcentricStreet = _query(
        """
        insert into CONCENTRIC_STREET (EVENT, ID, NAME)
        values (({query_eventID}), ?, ?)
        """
    )


    def _eventAccess(self, event, mode):
        try:
            for row in self._db.execute(
                self._query_eventAccess, (event.id, mode)
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
        event.validate()

        try:
            with self._db as db:
                cursor = db.cursor()
                try:
                    self.log.info(
                        "Clearing access: {event} {mode}",
                        event=event, mode=mode
                    )
                    cursor.execute(
                        self._query_clearEventAccess, (event.id, mode)
                    )
                    for expression in frozenset(expressions):
                        self.log.info(
                            "Adding access: {event} {mode} {expression}",
                            event=event, mode=mode, expression=expression
                        )
                        cursor.execute(
                            self._query_addEventAccess,
                            (event.id, expression, mode)
                        )
                finally:
                    cursor.close()
        except SQLiteError as e:
            self.log.critical(
                "Unable to set {mode} access for event: {event}",
                event=event, mode=mode, expressions=expressions
            )
            raise StorageError(e)

        self.log.info(
            "Set {mode} access for {event}: {expressions}",
            storeWriteClass=Event,
            event=event, mode=mode, expressions=expressions,
        )

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
        assert type(event) is Event

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
        assert type(event) is Event

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
        fileName = ":memory:"
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
            return "[{},{}] {}".format(
                self.nestingOrder, self.selectFrom, self.details
            )


    def __init__(self, name, query, lines):
        self.name  = name
        self.query = query
        self.lines = tuple(lines)


    def __str__(self):
        return str(self.asText())


    def asText(self):
        text = ["{}:".format(self.name), "", "  -- query --", ""]

        text.extend(
            "    {}".format(l)
            for l in self.query.strip().split("\n")
        )

        if self.lines:
            text.extend(("", "  -- query plan --", ""))
            text.extend("    {}".format(l.asText()) for l in self.lines)

        return "\n".join(text)



zeroTimeDelta = TimeDelta(0)


def asTimeStamp(datetime):
    assert datetime.tzinfo is not None, repr(datetime)
    assert datetime.tzinfo.utcoffset(datetime) == zeroTimeDelta

    return timegm(datetime.timetuple())


def fromTimeStamp(timestamp):
    return DateTime.fromtimestamp(timestamp, tz=utc)
