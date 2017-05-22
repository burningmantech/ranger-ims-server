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
from typing import Iterable
from typing.io import TextIO

from twisted.logger import Logger

from .._abc import IMSDataStore
from .._exceptions import StorageError
from ...ext.attr import attrib, attrs, instanceOf, optional
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
    class State(object):
        """
        Internal mutable state for :class:`Connection`.
        """

        db = attrib(
            validator=optional(instanceOf(Connection)),
            default=None, init=False,
        )

    dbPath = attrib(validator=instanceOf(Path))
    _state = attrib(default=State(), init=False)


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
                db = openDB(self.dbPath, schema=self._schema)
            except SQLiteError as e:
                raise StorageError(e)
            self._state.db = db

        return self._state.db


    async def events(self) -> Iterable[Event]:
        """
        Look up all events in this store.
        """
        raise NotImplementedError()


    async def createEvent(self, event: Event) -> None:
        """
        Create an event with the given name.
        """
        raise NotImplementedError()


    async def incidentTypes(
        self, includeHidden: bool = False
    ) -> Iterable[str]:
        """
        Look up the incident types used in this store.
        """
        raise NotImplementedError()


    async def createIncidentType(
        self, incidentType: str, hidden: bool = False
    ) -> None:
        """
        Create the given incident type.
        """
        raise NotImplementedError()


    async def showIncidentTypes(self, incidentTypes: Iterable[str]) -> None:
        """
        Show the given incident types.
        """
        raise NotImplementedError()


    async def hideIncidentTypes(self, incidentTypes: Iterable[str]) -> None:
        """
        Hide the given incident types.
        """
        raise NotImplementedError()


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
