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
from textwrap import dedent
from typing import Any, Dict, Iterable, Tuple
from typing.io import TextIO

from attr import Factory, attrib, attrs
from attr.validators import instance_of, optional

from twisted.logger import Logger

from .._abc import IMSDataStore
from .._exceptions import StorageError
from ...ext.sqlite import (
    Connection, SQLiteError, createDB, openDB, printSchema
)
from ...model import Event, Incident, Ranger


__all__ = ()



@attrs(frozen=True)
class DataStore(IMSDataStore):
    """
    Incident Management System SQLite data store.
    """

    _log = Logger()
    _schema = None

    @attrs(frozen=False)
    class _State(object):
        """
        Internal mutable state for :class:`Connection`.
        """

        db = attrib(
            validator=optional(instance_of(Connection)),
            default=None, init=False,
        )

    dbPath = attrib(validator=instance_of(Path))           # type: Path
    _state = attrib(default=Factory(_State), init=False)  # type: _State


    @classmethod
    def _loadSchema(cls) -> str:
        if cls._schema is None:
            path = Path(__file__).parent / "schema.sqlite"
            schema = path.read_text()
            cls._schema = schema
        return cls._schema


    @classmethod
    def printSchema(cls, out: TextIO) -> None:
        """
        Print schema.
        """
        with createDB(None, cls._loadSchema()) as db:
            printSchema(db, out=out)


    @property
    def _db(self) -> Connection:
        if self._state.db is None:
            try:
                db = openDB(self.dbPath, schema=self._loadSchema())
            except SQLiteError as e:
                raise StorageError(e)
            self._state.db = db

        return self._state.db


    def _execute(
        self, queries: Iterable[Tuple[str, Dict[str, Any]]],
        errorLogFormat: str,
    ) -> None:
        try:
            with self._db as db:
                for (query, queryArgs) in queries:
                    db.execute(query, queryArgs)
        except SQLiteError as e:
            self._log.critical(errorLogFormat, query=query, **queryArgs)
            raise StorageError(e)


    def _executeGenerator(
        self, query: str, queryArgs: Dict[str, Any], errorLogFormat: str
    ) -> Iterable[Any]:
        try:
            for row in self._db.execute(query, queryArgs):
                yield row
        except SQLiteError as e:
            self._log.critical(errorLogFormat, query=query, **queryArgs)
            raise StorageError(e)


    async def events(self) -> Iterable[Event]:
        """
        Look up all events in this store.
        """
        return (
            Event(row["name"]) for row in self._executeGenerator(
                self._query_events, {}, "Unable to look up events"
            )
        )

    _query_events = dedent(
        """
        select NAME from EVENT
        """
    )


    async def createEvent(self, event: Event) -> None:
        """
        Create an event with the given name.
        """
        self._execute(
            (
                (self._query_createEvent, dict(eventID=event.id)),
            ),
            "Unable to create event: {eventID}"
        )

    _query_createEvent = dedent(
        """
        insert into EVENT (NAME) values (:eventID);
        """
    )


    async def incidentTypes(
        self, includeHidden: bool = False
    ) -> Iterable[str]:
        """
        Look up the incident types used in this store.
        """
        if includeHidden:
            query = self._query_incidentTypes
        else:
            query = self._query_incidentTypesNotHidden

        return (
            row["name"] for row in self._executeGenerator(
                query, {}, "Unable to look up incident types"
            )
        )

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


    async def createIncidentType(
        self, incidentType: str, hidden: bool = False
    ) -> None:
        """
        Create the given incident type.
        """
        self._execute(
            (
                (
                    self._query_createIncidentType,
                    dict(name=incidentType, hidden=hidden),
                ),
            ),
            "Unable to create event: {eventID}"
        )

    _query_createIncidentType = dedent(
        """
        insert into INCIDENT_TYPE (NAME, HIDDEN)
        values (:name, :hidden)
        """
    )


    def _hideShowIncidentTypes(
        self, incidentTypes: Iterable[str], hidden: bool
    ) -> None:
        if hidden:
            action = "hide"
        else:
            action = "show"

        self._execute(
            (
                (
                    self._query_hideShowIncidentType,
                    dict(name=incidentType, hidden=hidden),
                )
                for incidentType in incidentTypes
            ),
            "Unable to {} incident types: {{incidentTypes}}".format(action)
        )

    _query_hideShowIncidentType = dedent(
        """
        update INCIDENT_TYPE set HIDDEN = :hidden where NAME = :name
        """
    )


    async def showIncidentTypes(self, incidentTypes: Iterable[str]) -> None:
        """
        Show the given incident types.
        """
        return self._hideShowIncidentTypes(incidentTypes, False)


    async def hideIncidentTypes(self, incidentTypes: Iterable[str]) -> None:
        """
        Hide the given incident types.
        """
        return self._hideShowIncidentTypes(incidentTypes, True)


    async def incidents(self, event: Event) -> Iterable[Incident]:
        """
        Look up all incidents for the given event.
        """
        raise NotImplementedError()


    async def incidentWithNumber(self, event: Event, number: int) -> Incident:
        """
        Look up the incident with the given number in the given event.
        """
        raise NotImplementedError()


    async def createIncident(
        self, event: Event, incident: Incident, author: Ranger
    ) -> None:
        """
        Create a new incident and add it into the given event.
        The incident number is determined by the database and must not be
        specified by the given incident.
        """
        raise NotImplementedError()
