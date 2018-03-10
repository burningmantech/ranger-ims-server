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

from datetime import datetime as DateTime, timezone as TimeZone
from pathlib import Path
from sys import stdout
from typing import Any, Callable, Optional
from typing.io import TextIO

from attr import Factory, attrib, attrs
from attr.validators import instance_of, optional

from twisted.logger import Logger

from ims.ext.json import objectFromJSONBytesIO
from ims.ext.sqlite import (
    Connection, SQLiteError, createDB, explainQueryPlans, openDB, printSchema
)
from ims.model import (
    Event, Incident, IncidentPriority, IncidentState
)
from ims.model.json import IncidentJSONKey, modelObjectFromJSONObject

from ._queries import queries
from .._db import DatabaseStore, ParameterValue, Parameters, Query, Rows
from .._exceptions import StorageError


__all__ = ()


query_eventID = "select ID from EVENT where NAME = :eventID"



@attrs(frozen=True)
class DataStore(DatabaseStore):
    """
    Incident Management System SQLite data store.
    """

    _log = Logger()

    schemaVersion = 2
    schemaBasePath = Path(__file__).parent / "schema"
    sqlFileExtension = "sqlite"

    query = queries


    @attrs(frozen=False)
    class _State(object):
        """
        Internal mutable state for :class:`DataStore`.
        """

        db: Optional[Connection] = attrib(
            validator=optional(instance_of(Connection)),
            default=None, init=False,
        )

    dbPath: Path = attrib(validator=instance_of(Path))
    _state: _State = attrib(default=Factory(_State), init=False)


    @classmethod
    def printSchema(cls, out: TextIO = stdout) -> None:
        """
        Print schema.
        """
        with createDB(None, cls.loadSchema()) as db:
            version = cls._dbSchemaVersion(db)
            print(f"Version: {version}", file=out)
            printSchema(db, out=out)


    @classmethod
    def printQueries(cls, out: TextIO = stdout) -> None:
        """
        Print a summary of queries.
        """
        queries = (
            (getattr(cls.query, name).text, name)
            for name in sorted(vars(cls.query))
        )

        with createDB(None, cls.loadSchema()) as db:
            for line in explainQueryPlans(db, queries):
                print(line, file=out)
                print(file=out)


    @classmethod
    def _dbSchemaVersion(cls, db: Connection) -> int:
        try:
            for row in db.execute(cls.query.schemaVersion.text):
                return row["VERSION"]
            else:
                raise StorageError("Invalid schema: no version")

        except SQLiteError as e:
            if e.args[0] == "no such table: SCHEMA_INFO":
                return 0

            cls._log.critical(
                "Unable to {description}: {error}",
                description=cls.query.schemaVersion.description, error=e,
            )
            raise StorageError(e)


    @property
    def _db(self) -> Connection:
        if self._state.db is None:
            try:
                self._state.db = openDB(self.dbPath, schema="")

            except SQLiteError as e:
                self._log.critical(
                    "Unable to open SQLite database {dbPath}: {error}",
                    dbPath=self.dbPath, error=e,
                )
                raise StorageError(
                    f"Unable to open SQLite database {self.dbPath}: {e}"
                )

        return self._state.db


    async def disconnect(self) -> None:
        """
        See :meth:`DatabaseStore.disconnect`.
        """
        self._state.db = None


    async def runQuery(
        self, query: Query, parameters: Optional[Parameters] = None
    ) -> Rows:
        if parameters is None:
            parameters = {}

        try:
            return self._db.execute(query.text, parameters)

        except SQLiteError as e:
            self._log.critical(
                "Unable to {description}: {error}",
                description=query.description,
                query=query, **parameters, error=e,
            )
            raise StorageError(e)


    async def runOperation(
        self, query: Query, parameters: Optional[Parameters] = None
    ) -> None:
        await self.runQuery(query, parameters)


    async def runInteraction(self, interaction: Callable) -> Any:
        try:
            with self._db as db:
                return interaction(db.cursor())
        except SQLiteError as e:
            self._log.critical(
                "Interaction {interaction} failed: {error}",
                interaction=interaction, error=e,
            )
            raise StorageError(e)


    async def dbSchemaVersion(self) -> int:
        """
        See :meth:`DatabaseStore.dbSchemaVersion`.
        """
        return self._dbSchemaVersion(self._db)


    async def applySchema(self, sql: str) -> None:
        """
        See :meth:`IMSDataStore.applySchema`.
        """
        try:
            self._db.executescript(sql)
            self._db.validateConstraints()
            self._db.commit()
        except SQLiteError as e:
            raise StorageError(f"Unable to apply schema: {e}")


    def asIncidentStateValue(
        self, incidentState: IncidentState
    ) -> ParameterValue:
        return incidentStateAsID(incidentState)


    def fromIncidentStateValue(self, value: ParameterValue) -> IncidentState:
        return incidentStateFromID(value)


    def asPriorityValue(self, priority: IncidentPriority) -> ParameterValue:
        return priorityAsID(priority)


    def fromPriorityValue(self, value: ParameterValue) -> IncidentPriority:
        return priorityFromID(value)


    def asDateTimeValue(self, dateTime: DateTime) -> ParameterValue:
        return asTimeStamp(dateTime)


    def fromDateTimeValue(self, value: ParameterValue) -> DateTime:
        return fromTimeStamp(value)


    async def validate(self) -> None:
        """
        See :meth:`IMSDataStore.validate`.
        """
        self._log.info("Validating data store...")

        valid = True

        try:
            self._db.validateConstraints()
        except SQLiteError as e:
            self._log.error(
                "Database constraint violated: {error}",
                error=e,
            )

        # Check for detached report entries
        for reportEntry in await self.detachedReportEntries():
            self._log.error(
                "Found detached report entry: {reportEntry}",
                reportEntry=reportEntry,
            )
            valid = False

        if not valid:
            raise StorageError("Data store validation failed")


    def loadFromEventJSON(
        self, event: Event, path: Path, trialRun: bool = False
    ) -> None:
        """
        Load event data from a file containing JSON.
        """
        with path.open() as fileHandle:
            eventJSON = objectFromJSONBytesIO(fileHandle)

            self._log.info("Creating event: {event}", event=event)
            self.createEvent(event)

            # Load incidents
            for incidentJSON in eventJSON:
                try:
                    eventID = incidentJSON.get(IncidentJSONKey.event.value)
                    if eventID is None:
                        incidentJSON[IncidentJSONKey.event.value] = event.id
                    else:
                        if eventID != event.id:
                            raise ValueError(
                                f"Event ID {eventID} != {event.id}"
                            )

                    incident = modelObjectFromJSONObject(
                        incidentJSON, Incident
                    )
                except ValueError as e:
                    if trialRun:
                        number = incidentJSON.get(IncidentJSONKey.number.value)
                        self._log.critical(
                            "Unable to load incident #{number}: {error}",
                            number=number, error=e,
                        )
                    else:
                        raise

                for incidentType in incident.incidentTypes:
                    self.createIncidentType(incidentType, hidden=True)

                self._log.info(
                    "Creating incident in {event}: {incident}",
                    event=event, incident=incident
                )
                if not trialRun:
                    self.importIncident(incident)



def asTimeStamp(dateTime: DateTime) -> float:
    assert dateTime.tzinfo is not None, repr(dateTime)
    timeStamp = dateTime.timestamp()
    if timeStamp < 0:
        raise StorageError(
            f"DateTime is before the UTC epoch: {dateTime}"
        )
    return timeStamp


def fromTimeStamp(timeStamp: ParameterValue) -> DateTime:
    if not isinstance(timeStamp, float):
        raise TypeError("Time stamp in SQLite store must be a float")

    return DateTime.fromtimestamp(timeStamp, tz=TimeZone.utc)


def incidentStateFromID(strValue: ParameterValue) -> IncidentState:
    if not isinstance(strValue, str):
        raise TypeError("Incident state in SQLite store must be a str")

    return {
        "new":        IncidentState.new,
        "on_hold":    IncidentState.onHold,
        "dispatched": IncidentState.dispatched,
        "on_scene":   IncidentState.onScene,
        "closed":     IncidentState.closed,
    }[strValue]


def incidentStateAsID(incidentState: IncidentState) -> str:
    return {
        IncidentState.new:        "new",
        IncidentState.onHold:     "on_hold",
        IncidentState.dispatched: "dispatched",
        IncidentState.onScene:    "on_scene",
        IncidentState.closed:     "closed",
    }[incidentState]


def priorityFromID(intValue: ParameterValue) -> IncidentPriority:
    if not isinstance(intValue, int):
        raise TypeError("Incident priority in SQLite store must be an int")

    return {
        1: IncidentPriority.high,
        2: IncidentPriority.high,
        3: IncidentPriority.normal,
        4: IncidentPriority.low,
        5: IncidentPriority.low,
    }[intValue]


def priorityAsID(priority: IncidentPriority) -> int:
    return {
        IncidentPriority.high:   1,
        IncidentPriority.normal: 3,
        IncidentPriority.low:    4,
    }[priority]
