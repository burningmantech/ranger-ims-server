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

import sys

from textwrap import dedent
from sqlite3 import connect, Row as LameRow, OperationalError

from twisted.python.filepath import FilePath
from twisted.logger import Logger
from twext.python.usage import exit, ExitStatus

from ..data.model import TextOnlyAddress, RodGarettAddress
from .file import MultiStorage



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


    @classmethod
    def loadFiles(cls, args=sys.argv):
        if len(args) < 3:
            exit(ExitStatus.EX_USAGE, "Too few arguments")

        dbPath     = args[1]
        storePaths = args[2:]

        storage = cls(FilePath(dbPath))

        for storePath in storePaths:
            storage.loadFromFileStore(FilePath(storePath))


    def __init__(self, dbFilePath):
        self.dbFilePath = dbFilePath
        self._db = openDB(dbFilePath, create=True)


    def loadFromFileStore(self, filePath):
        """
        Load data from a legacy file store.
        """
        multiStore = MultiStorage(filePath, readOnly=True)

        for event in multiStore:
            self.createEvent(event)

            eventStore = multiStore[event]

            for number, etag in eventStore.listIncidents():
                incident = eventStore.readIncidentWithNumber(number)

                for incidentType in incident.incidentTypes:
                    self.createIncidentType(incidentType, hidden=True)

                self.createIncident(event, incident)


    def events(self):
        """
        Look up all events in this store.
        """
        for row in self._db.execute(self._query_events):
            yield row.NAME

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

    def createEvent(self, name):
        """
        Create an event with the given name.
        """
        self._db.execute(self._query_createEvent, (name,))
        self._db.commit()

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

        for row in self._db.execute(query):
            yield row.NAME

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


    def createIncidentType(self, name, hidden=False):
        """
        Create an incident type with the given name.
        """
        self._db.execute(self._query_createIncidentType, (name, hidden))
        self._db.commit()

    _query_createIncidentType = dedent(
        """
        insert or ignore into INCIDENT_TYPE (NAME, HIDDEN) values (?, ?)
        """
    )


    def incidentETag(self, event, number):
        """
        Look up the ETag for the incident with the given number in the given
        event.
        """
        self._db.execute(self._query_version, (event, number))

    _query_version = dedent(
        """
        select VERSION from INCIDENT
        where EVENT = ({query_eventID}) and NUMBER = ?
        """
        .format(query_eventID=_query_eventID.strip())
    )


    def readIncident(self, event, number):
        """
        Look up the incident with the given number in the given event.
        """
        raise NotImplementedError()


    def createIncident(self, event, incident):
        """
        Write the given incident into the given event.
        """
        incident.validate()

        location = incident.location

        if location is None:
            locationName = None
            address = RodGarettAddress()
        else:
            locationName = location.name
            if location.address is None:
                address = RodGarettAddress()
            elif isinstance(location.address, TextOnlyAddress):
                address = RodGarettAddress(
                    description=location.address.description,
                )
            elif isinstance(location.address, RodGarettAddress):
                address = location.address
            else:
                raise AssertionError(
                    "Unknown address type: {!r}".format(location.address)
                )

        try:
            self._db.execute(
                self._query_addIncident, (
                    event,
                    incident.number,
                    1,
                    incident.priority,
                    incident.summary,
                    incident.created,
                    incident.state.name,
                    locationName,
                    address.concentric,
                    address.radialHour,
                    address.radialMinute,
                    address.description,
                )
            )

            for ranger in incident.rangers:
                self._db.execute(
                    self._query_attachRanger,
                    (event, incident.number, ranger.handle)
                )

            for incidentType in incident.incidentTypes:
                self._db.execute(
                    self._query_attachIncidentType,
                    (event, incident.number, incidentType)
                )

            for reportEntry in incident.reportEntries:
                self._db_execute(
                    self._query_addReportEntry,
                    (
                        reportEntry.author.handle,
                        reportEntry.text,
                        reportEntry.created,
                        reportEntry.system_entry,
                    )
                )
                self._db_execute(
                    self._query_attachReportEntry,
                    (event, incident.number, NotImplemented)
                )

            self._db.commit()
        except Exception:
            self.log.critical(
                "Unable to write incident to event {event}: {incident!r}",
                incident=incident, event=event
            )
            raise

    _query_addIncident = dedent(
        """
        insert into INCIDENT (
            EVENT,
            NUMBER,
            VERSION,
            PRIORITY,
            SUMMARY,
            CREATED,
            STATE,
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
        values ({query_eventID}, ?, ?)
        """
        .format(query_eventID=_query_eventID.strip())
    )


    def readers(self):
        return ("*",)


    def writers(self):
        return ()


    def explainQueryPlans(self):
        queries = [
            (getattr(self, k), k[7:])
            for k in vars(self.__class__).iterkeys()
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
