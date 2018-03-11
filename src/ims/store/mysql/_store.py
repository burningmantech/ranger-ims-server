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
Incident Management System SQL data store.
"""

from datetime import datetime as DateTime
from pathlib import Path
from typing import Any, Callable, Optional, cast

from attr import Factory, attrib, attrs
from attr.validators import instance_of, optional

from pymysql.cursors import DictCursor as Cursor
from pymysql.err import MySQLError

from twisted.enterprise.adbapi import ConnectionPool
from twisted.logger import Logger

from ims.model import IncidentPriority, IncidentState

from ._queries import queries
from .._db import DatabaseStore, ParameterValue, Parameters, Query, Rows
from .._exceptions import StorageError


__all__ = ()



@attrs(frozen=True)
class DataStore(DatabaseStore):
    """
    Incident Management System MySQL data store.
    """

    _log = Logger()

    schemaVersion = 2
    schemaBasePath = Path(__file__).parent / "schema"
    sqlFileExtension = "mysql"

    query = queries


    @attrs(frozen=False)
    class _State(object):
        """
        Internal mutable state for :class:`DataStore`.
        """

        db: Optional[ConnectionPool] = attrib(
            validator=optional(instance_of(ConnectionPool)),
            default=None, init=False,
        )


    hostName: str = attrib(validator=instance_of(str))
    hostPort: str = attrib(validator=instance_of(int))
    database: str = attrib(validator=instance_of(str))
    username: str = attrib(validator=instance_of(str))
    password: str = attrib(validator=instance_of(str))

    _state: _State = attrib(default=Factory(_State), init=False)


    @staticmethod
    def asIncidentStateValue(incidentState: IncidentState) -> ParameterValue:
        raise NotImplementedError("asIncidentStateValue")


    @staticmethod
    def fromIncidentStateValue(value: ParameterValue) -> IncidentState:
        raise NotImplementedError("fromIncidentStateValue")


    @staticmethod
    def asPriorityValue(priority: IncidentPriority) -> ParameterValue:
        raise NotImplementedError("asPriorityValue")


    @staticmethod
    def fromPriorityValue(value: ParameterValue) -> IncidentPriority:
        raise NotImplementedError("fromPriorityValue")


    @staticmethod
    def asDateTimeValue(dateTime: DateTime) -> ParameterValue:
        raise NotImplementedError("asDateTimeValue")


    @staticmethod
    def fromDateTimeValue(value: ParameterValue) -> DateTime:
        raise NotImplementedError("fromDateTimeValue")


    @property
    def _db(self) -> ConnectionPool:
        if self._state.db is None:
            db = ConnectionPool(
                "pymysql",
                host=self.hostName,
                port=self.hostPort,
                database=self.database,
                user=self.username,
                password=self.password,
                cursorclass=Cursor,
                cp_reconnect=True,
            )

            # self._upgradeSchema(db)

            self._state.db = db

        return self._state.db


    async def disconnect(self) -> None:
        """
        See :meth:`DatabaseStore.disconnect`.
        """
        if self._state.db is not None:
            self._state.db.close()
            self._state.db = None


    async def runQuery(
        self, query: Query, parameters: Optional[Parameters] = None
    ) -> Rows:
        if parameters is None:
            parameters = {}

        try:
            return iter(await self._db.runQuery(query.text, parameters))

        except MySQLError as e:
            self._log.critical(
                "Unable to {description}: {error}",
                description=query.description,
                query=query, **parameters, error=e,
            )
            raise StorageError(e)


    async def runOperation(
        self, query: Query, parameters: Optional[Parameters] = None
    ) -> None:
        if parameters is None:
            parameters = {}

        try:
            await self._db.runOperation(query.text, parameters)

        except MySQLError as e:
            self._log.critical(
                "Unable to {description}: {error}",
                description=query.description, error=e,
            )
            raise StorageError(e)


    async def runInteraction(
        self, interaction: Callable, *args: Any, **kwargs: Any
    ) -> Any:
        try:
            return await self._db.runInteraction(interaction, *args, **kwargs)
        except MySQLError as e:
            self._log.critical(
                "Interaction {interaction} failed: {error}",
                interaction=interaction, error=e,
            )
            raise StorageError(e)


    async def dbSchemaVersion(self) -> int:
        """
        See `meth:DatabaseStore.dbSchemaVersion`.
        """
        try:
            for row in await self._db.runQuery(self.query.schemaVersion.text):
                return cast(int, row["VERSION"])
            else:
                raise StorageError("Invalid schema: no version")

        except MySQLError as e:
            message = e.args[1]
            if (
                message.startswith("Table '") and
                message.endswith(".SCHEMA_INFO' doesn't exist")
            ):
                return 0

            self._log.critical(
                "Unable to {description}: {error}",
                description=self.query.schemaVersion.description, error=e,
            )
            raise StorageError(e)


    async def applySchema(self, sql: str) -> None:
        """
        See :meth:`IMSDataStore.applySchema`.
        """
        def applySchema(txn: Cursor) -> None:
            # FIXME: OMG this is gross but works for now
            for statement in sql.split(";"):
                statement = statement.strip()
                if statement and not statement.startswith("--"):
                    txn.execute(statement)

        try:
            await self.runInteraction(applySchema)
        except StorageError as e:
            self._log.critical(
                "Unable to apply schema: {error}", sql=sql, error=e
            )
            raise StorageError(f"Unable to apply schema: {e}")
