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

from ..tz import utc
from ..data.model import (
    Incident, IncidentState, Ranger, ReportEntry,
    Location, RodGarettAddress,
    InvalidDataError,
)
from ._file import MultiStorage
from .istore import StorageError



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
        try:
            self._db = openDB(dbFilePath, create=True)
            self._db.execute("pragma foreign_keys = ON")
        except SQLiteError as e:
            raise StorageError(e)


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

            # Load incidents
            for number, etag in eventStore.listIncidents():
                incident = eventStore.readIncidentWithNumber(number)

                for incidentType in incident.incidentTypes:
                    self.createIncidentType(incidentType, hidden=True)

                self.log.info(
                    "Creating incident: {incident}", incident=incident
                )
                self.createIncident(event, incident)

            # Load concentric street names
            for name, id in eventStore.streetsByName().items():
                self.log.info(
                    "Creating concentric street: {event}: {name}",
                    event=event, name=name
                )
                self.createConcentricStreet(event, id, name)

            # Load access
            self.setReaders(event, eventStore.readers())
            self.setWriters(event, eventStore.writers())


    def events(self):
        """
        Look up all events in this store.
        """
        try:
            for row in self._db.execute(self._query_events):
                yield row[0]
        except SQLiteError as e:
            self.log.critical("Unable to look up events")
            raise StorageError(e)

    _query_events = dedent(
        """
        select NAME from EVENT
        """
    )

    _query_eventID = dedent(
        """
        select ID from EVENT where NAME = ?
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


    def incidentTypes(self, includeHidden=True):
        """
        Look up all events in this store.
        """
        if includeHidden:
            query = self._query_incidentTypes
        else:
            query = self._query_incidentTypesNotHidden

        try:
            for row in self._db.execute(query):
                yield row[0]
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


    # def incidentETag(self, event, number):
    #     """
    #     Look up the ETag for the incident with the given number in the given
    #     event.
    #     """
    #     try:
    #         cursor = self._db.execute(self._query_version, (event, number))
    #         return cursor.fetchone()[0]
    #     except SQLiteError as e:
    #         self.log.critical("Unable to look up ETag")
    #         raise StorageError(e)

    # _query_version = dedent(
    #     """
    #     select VERSION from INCIDENT
    #     where EVENT = ({query_eventID}) and NUMBER = ?
    #     """
    #     .format(query_eventID=_query_eventID.strip())
    # )


    def incident(self, event, number):
        """
        Look up the incident with the given number in the given event.
        """
        try:
            # Fetch incident row
            (
                number, version, createdTimestamp, priority, stateName,
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
                Ranger(handle=row[0], name=None, status=None)
                for row in self._db.execute(
                    self._query_incident_rangers, (event, number)
                )
            )

            # Look up incident types from join table
            incidentTypes = (
                row[0] for row in self._db.execute(
                    self._query_incident_types, (event, number)
                )
            )

            # Look up report entries from join table
            reportEntries = []

            for author, text, createdTimeStamp, generated in self._db.execute(
                self._query_incident_reportEntries, (event, number)
            ):
                reportEntries.append(
                    ReportEntry(
                        author=author,
                        text=text,
                        created=fromTimeStamp(createdTimestamp),
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

    _query_incident = dedent(
        """
        select
            NUMBER, VERSION, CREATED, PRIORITY, STATE, SUMMARY,
            LOCATION_NAME,
            LOCATION_CONCENTRIC,
            LOCATION_RADIAL_HOUR,
            LOCATION_RADIAL_MINUTE,
            LOCATION_DESCRIPTION
        from INCIDENT where EVENT = ({query_eventID}) and NUMBER = ?
        """
        .format(query_eventID=_query_eventID.strip())
    )

    _query_incident_rangers = dedent(
        """
        select RANGER_HANDLE from INCIDENT__RANGER
        where EVENT = ({query_eventID}) and INCIDENT_NUMBER = ?
        """
        .format(query_eventID=_query_eventID.strip())
    )

    _query_incident_types = dedent(
        """
        select NAME from INCIDENT_TYPE where ID in (
            select INCIDENT_TYPE from INCIDENT__INCIDENT_TYPE
            where EVENT = ({query_eventID}) and INCIDENT_NUMBER = ?
        )
        """
        .format(query_eventID=_query_eventID.strip())
    )

    _query_incident_reportEntries = dedent(
        """
        select AUTHOR, TEXT, CREATED, GENERATED from REPORT_ENTRY
        where ID in (
            select REPORT_ENTRY from INCIDENT__REPORT_ENTRY
            where EVENT = ({query_eventID}) and INCIDENT_NUMBER = ?
        )
        """
        .format(query_eventID=_query_eventID.strip())
    )


    def _incidentNumbers(self, event):
        """
        Look up all incident numbers for the given event.
        """
        try:
            for row in self._db.execute(self._query_incidentNumbers, (event,)):
                yield row[0]
        except SQLiteError as e:
            self.log.critical(
                "Unable to look up incident numbers for event: {event}",
                event=event
            )
            raise StorageError(e)

    _query_incidentNumbers = dedent(
        """
        select NUMBER from INCIDENT where EVENT = ({query_eventID})
        """
        .format(query_eventID=_query_eventID.strip())
    )


    def incidents(self, event):
        """
        Look up all incidents for the given event.
        """
        for number in self._incidentNumbers(event):
            yield self.incident(event, number)


    def createIncident(self, event, incident):
        """
        Create the given incident into the given event.
        """
        incident.validate()

        # Make sure location name and address are not None.
        # Coerce all location addresses into Rod Garett form.
        location = incident.location

        if location is None:
            locationName = None
            address = RodGarettAddress()
        else:
            locationName = location.name
            if location.address is None:
                address = RodGarettAddress()
            else:
                address = location.address.asRodGarettAddress()

        try:
            with self._db as db:
                cursor = db.cursor()
                try:
                    # Write incident row, version is 1 because it's a new row
                    cursor.execute(
                        self._query_addIncident, (
                            event,
                            incident.number,
                            1,
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

                    # Join with Ranger handles
                    for ranger in incident.rangers:
                        cursor.execute(
                            self._query_attachRanger,
                            (event, incident.number, ranger.handle)
                        )

                    # Join with incident types
                    for incidentType in incident.incidentTypes:
                        cursor.execute(
                            self._query_attachIncidentType,
                            (event, incident.number, incidentType)
                        )

                    for reportEntry in incident.reportEntries:
                        # Create report entry row
                        cursor.execute(
                            self._query_addReportEntry,
                            (
                                reportEntry.author,
                                reportEntry.text,
                                asTimeStamp(reportEntry.created),
                                reportEntry.system_entry,
                            )
                        )
                        # Join to incident
                        cursor.execute(
                            self._query_attachReportEntry,
                            (event, incident.number, cursor.lastrowid)
                        )

                finally:
                    cursor.close()

        except SQLiteError as e:
            self.log.critical(
                "Unable to write incident to event {event}: {incident!r}",
                incident=incident, event=event
            )
            raise StorageError(e)

    _query_addIncident = dedent(
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
        values (
            ({query_eventID}),
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """
        .format(query_eventID=_query_eventID.strip())
    )

    _query_attachRanger = dedent(
        """
        insert into INCIDENT__RANGER (
            EVENT, INCIDENT_NUMBER, RANGER_HANDLE
        )
        values (
            ({query_eventID}), ?, ?
        )
        """
        .format(query_eventID=_query_eventID.strip())
    )

    _query_attachIncidentType = dedent(
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
        .format(query_eventID=_query_eventID.strip())
    )

    _query_addReportEntry = dedent(
        """
        insert into REPORT_ENTRY (AUTHOR, TEXT, CREATED, GENERATED)
        values (?, ?, ?, ?)
        """
    )

    _query_attachReportEntry = dedent(
        """
        insert into INCIDENT__REPORT_ENTRY (
            EVENT, INCIDENT_NUMBER, REPORT_ENTRY
        )
        values (
            ({query_eventID}), ?, ?
        )
        """
        .format(query_eventID=_query_eventID.strip())
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

    _queryFormat_setIncidentColumn = dedent(
        """
        update INCIDENT set {{column}} = ?
        where EVENT = ({query_eventID}) and NUMBER = ?
        """
        .format(query_eventID=_query_eventID.strip())
    )


    def setIncidentPriority(self, event, number, priority):
        """
        Set the priority for the given incident in the given event.
        """
        self._setIncidentColumn(
            self._query_setIncidentPriority,
            event, number, "priority", priority
        )

    _query_setIncidentPriority = _setIncidentColumn.format(column="PRIORITY")


    def setIncidentState(self, event, number, state):
        """
        Set the state for the given incident in the given event.
        """
        self._setIncidentColumn(
            self._query_setIncidentState,
            event, number, "state", state
        )

    _query_setIncidentState = _setIncidentColumn.format(column="STATE")


    def setIncidentSummary(self, event, number, summary):
        """
        Set the summary for the given incident in the given event.
        """
        self._setIncidentColumn(
            self._query_setIncidentSummary,
            event, number, "summary", summary
        )

    _query_setIncidentSummary = _setIncidentColumn.format(column="SUMMARY")


    def setIncidentLocationName(self, event, number, name):
        """
        Set the location name for the given incident in the given event.
        """
        self._setIncidentColumn(
            self._query_setIncidentLocationName,
            event, number, "location name", name
        )

    _query_setIncidentLocationName = _setIncidentColumn.format(
        column="LOCATION_NAME"
    )


    def setIncidentLocationConcentricStreet(self, event, number, streetID):
        """
        Set the location concentric street for the given incident in the given
        event.
        """
        self._setIncidentColumn(
            self._query_setIncidentLocationConcentricStreet,
            event, number, "location concentric street", streetID
        )

    _query_setIncidentLocationConcentricStreet = _setIncidentColumn.format(
        column="LOCATION_CONCENTRIC"
    )


    def setIncidentLocationRadialHour(self, event, number, hour):
        """
        Set the location radial hour for the given incident in the given event.
        """
        self._setIncidentColumn(
            self._query_setIncidentLocationRadialHour,
            event, number, "location radial hour", hour
        )

    _query_setIncidentLocationRadialHour = _setIncidentColumn.format(
        column="LOCATION_RADIAL_HOUR"
    )


    def setIncidentLocationRadialMinute(self, event, number, minute):
        """
        Set the location radial minute for the given incident in the given
        event.
        """
        self._setIncidentColumn(
            self._query_setIncidentLocationRadialMinute,
            event, number, "location radial minute", minute
        )

    _query_setIncidentLocationRadialMinute = _setIncidentColumn.format(
        column="LOCATION_RADIAL_MINUTE"
    )


    def setIncidentLocationDescription(self, event, number, description):
        """
        Set the location description for the given incident in the given event.
        """
        self._setIncidentColumn(
            self._query_setIncidentLocationDescription,
            event, number, "location description", description
        )

    _query_setIncidentLocationDescription = _setIncidentColumn.format(
        column="LOCATION_DESCRIPTION"
    )


    def setIncidentRangers(self, event, number, handles):
        """
        Set the rangers attached to the given incident in the given event.
        """
        raise NotImplementedError()


    def setIncidentTypes(self, event, number, incidentTypes):
        """
        Set the incident types attached to the given incident in the given
        event.
        """
        raise NotImplementedError()


    def addIncidentReportEntry(self, event, number, reportEntry):
        """
        Add a report entry to the given incident in the given event.
        """
        raise NotImplementedError()


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

    _query_concentricStreets = dedent(
        """
        select ID, NAME from CONCENTRIC_STREET
        where EVENT = ({query_eventID})
        """
        .format(query_eventID=_query_eventID.strip())
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

    _query_addConcentricStreet = dedent(
        """
        insert into CONCENTRIC_STREET (EVENT, ID, NAME)
        values (({query_eventID}), ?, ?)
        """
        .format(query_eventID=_query_eventID.strip())
    )


    def _eventAccess(self, event, mode):
        try:
            for row in self._db.execute(
                self._query_eventAccess, (event, mode)
            ):
                yield row[0]
        except SQLiteError as e:
            self.log.critical(
                "Unable to look up {mode} access for event: {event}",
                event=event, mode=mode
            )
            raise StorageError(e)

    _query_eventAccess = dedent(
        """
        select EXPRESSION from EVENT_ACCESS
        where EVENT = ({query_eventID}) and MODE = ?
        """
        .format(query_eventID=_query_eventID.strip())
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
                    for expression in expressions:
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

    _query_clearEventAccess = dedent(
        """
        delete from EVENT_ACCESS
        where EVENT = ({query_eventID}) and MODE = ?
        """
        .format(query_eventID=_query_eventID.strip())
    )

    _query_addEventAccess = dedent(
        """
        insert into EVENT_ACCESS (EVENT, EXPRESSION, MODE)
        values (({query_eventID}), ?, ?)
        """
        .format(query_eventID=_query_eventID.strip())
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
    assert datetime.tzinfo is not None
    assert datetime.tzinfo.utcoffset(datetime) == zeroTimeDelta

    return timegm(datetime.timetuple())


def fromTimeStamp(timestamp):
    return DateTime.fromtimestamp(timestamp, tz=utc)
