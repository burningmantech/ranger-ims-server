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

from pathlib import Path
from sys import stdout
from typing import Any, Callable, ClassVar, Optional
from typing.io import TextIO

from attr import attrib, attrs

from twisted.logger import Logger

from ims.ext.json import objectFromJSONBytesIO
from ims.ext.sqlite import (
    Connection, SQLiteError, createDB, explainQueryPlans, openDB, printSchema
)
from ims.model import Event, Incident
from ims.model.json import IncidentJSONKey, modelObjectFromJSONObject

from ._queries import queries
from .._db import DatabaseStore, Parameters, Queries, Query, Rows
from .._exceptions import StorageError


__all__ = ()


query_eventID = "select ID from EVENT where NAME = :eventID"



@attrs(frozen=True, auto_attribs=True, kw_only=True)
class DataStore(DatabaseStore):
    """
    Incident Management System SQLite data store.
    """

    _log: ClassVar[Logger] = Logger()

    schemaVersion: ClassVar[int] = 4
    schemaBasePath: ClassVar[Path] = Path(__file__).parent / "schema"
    sqlFileExtension: ClassVar[str] = "sqlite"

    query: ClassVar[Queries] = queries


    @attrs(
        frozen=False, auto_attribs=True, kw_only=True, cmp=False
    )
    class _State(object):
        """
        Internal mutable state for :class:`DataStore`.
        """

        db: Optional[Connection] = attrib(default=None, init=False)


    dbPath: Path
    _state: _State = attrib(factory=_State, init=False)


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
            raise StorageError(str(e))


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
            raise StorageError(str(e))


    async def runOperation(
        self, query: Query, parameters: Optional[Parameters] = None
    ) -> None:
        await self.runQuery(query, parameters)


    async def runInteraction(
        self, interaction: Callable, *args: Any, **kwargs: Any
    ) -> Any:
        try:
            with self._db as db:
                return interaction(db.cursor(), *args, **kwargs)
        except SQLiteError as e:
            self._log.critical(
                "Interaction {interaction} failed: {error}",
                interaction=interaction, error=e,
            )
            raise StorageError(str(e))


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


    async def validate(self) -> None:
        """
        See :meth:`IMSDataStore.validate`.
        """
        await super().validate()

        valid = True

        try:
            self._db.validateConstraints()
        except SQLiteError as e:
            self._log.error(
                "Database constraint violated: {error}",
                error=e,
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
