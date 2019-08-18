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

from pathlib import Path
from sys import stdout
from typing import Any, Callable, ClassVar, Optional, cast
from typing.io import TextIO

from attr import attrib, attrs

from pymysql.cursors import DictCursor
from pymysql.err import MySQLError

from twisted.enterprise.adbapi import Connection, ConnectionPool
from twisted.logger import Logger

from ._queries import queries
from .._db import DatabaseStore, Parameters, Queries, Query, Rows, Transaction
from .._exceptions import StorageError


__all__ = ()



class ReconnectingConnectionPool(ConnectionPool):
    """
    Subclass of ConnectionPool that reconnects to MySQL.
    """

    def connect(self) -> Connection:
        connection = ConnectionPool.connect(self)
        connection.ping(reconnect=True)
        return connection



class Cursor(DictCursor):
    """
    Subclass of :class:`DictCursor` that adds logging of SQL statements for
    debugging purposes.
    """

    _log: ClassVar[Logger] = Logger()


    def execute(
        self, sql: str, parameters: Optional[Parameters] = None
    ) -> int:
        """
        See :meth:`sqlite3.Cursor.execute`.
        """
        if parameters is None:
            parameters = {}
        self._log.debug(
            "EXECUTE: {sql} <- {parameters}", sql=sql, parameters=parameters
        )
        return super().execute(sql, parameters)


    def executescript(self, sql_script: str) -> int:
        self._log.debug("Executing script", script=sql_script)

        count = 0

        # FIXME: OMG this is gross but works for now
        for statement in sql_script.split(";"):
            statement = statement.strip()
            if statement and not statement.startswith("--"):
                count += self.execute(statement)

        return count



@attrs(frozen=True, auto_attribs=True, kw_only=True)
class DataStore(DatabaseStore):
    """
    Incident Management System MySQL data store.
    """

    _log: ClassVar[Logger] = Logger()

    schemaVersion: ClassVar[int] = 4
    schemaBasePath: ClassVar[Path] = Path(__file__).parent / "schema"
    sqlFileExtension: ClassVar[str] = "mysql"

    query: ClassVar[Queries] = queries


    @attrs(frozen=False, auto_attribs=True, kw_only=True, cmp=False)
    class _State(object):
        """
        Internal mutable state for :class:`DataStore`.
        """

        db: Optional[ConnectionPool] = attrib(default=None, init=False)


    hostName: str
    hostPort: int
    database: str
    username: str
    password: str

    _state: _State = attrib(factory=_State, init=False)


    @property
    def _db(self) -> ConnectionPool:
        if self._state.db is None:
            db = ReconnectingConnectionPool(
                "pymysql",
                host=self.hostName,
                port=self.hostPort,
                database=self.database,
                user=self.username,
                password=self.password,
                cursorclass=Cursor,
                cp_reconnect=True,
            )

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
            raise StorageError(str(e))


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
            raise StorageError(str(e))


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
            raise StorageError(str(e))


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
            raise StorageError(str(e))


    async def printSchema(self, out: TextIO = stdout) -> None:
        """
        Print schema.
        """
        # See https://dev.mysql.com/doc/refman/5.7/en/tables-table.html

        version = await self.dbSchemaVersion()
        print(f"Version: {version}", file=out)

        columnsQuery = Query(
            "look up database columns",
            """
            select
                TABLE_NAME,
                COLUMN_NAME,
                DATA_TYPE,
                CHARACTER_MAXIMUM_LENGTH,
                IS_NULLABLE,
                COLUMN_DEFAULT,
                ORDINAL_POSITION
            from INFORMATION_SCHEMA.COLUMNS
            where TABLE_SCHEMA = database()
            order by TABLE_NAME, ORDINAL_POSITION
            """
        )

        lastTableName = ""

        for row in await self.runQuery(columnsQuery):
            tableName      = row["TABLE_NAME"]
            columnName     = row["COLUMN_NAME"]
            columnType     = row["DATA_TYPE"]
            columnMaxChars = row["CHARACTER_MAXIMUM_LENGTH"]
            columnNullable = row["IS_NULLABLE"]
            columnDefault  = row["COLUMN_DEFAULT"]
            columnPosition = row["ORDINAL_POSITION"]

            if tableName != lastTableName:
                print(f"{tableName}:", file=out)
                lastTableName = cast(str, tableName)

            if columnMaxChars is None:
                size = ""
            else:
                size = f"({columnMaxChars})"

            if columnNullable == "YES":
                notNull = ""
            else:
                notNull = " not null"

            if columnDefault:
                default = f" := {columnDefault}"
            else:
                default = ""

            text = (
                f"  {columnPosition}: "
                f"{columnName}({columnType}{size}){notNull}{default}"
            )

            print(text, file=out)


    async def applySchema(self, sql: str) -> None:
        """
        See :meth:`IMSDataStore.applySchema`.
        """
        def applySchema(txn: Transaction) -> None:
            txn.executescript(sql)

        try:
            await self.runInteraction(applySchema)
        except StorageError as e:
            self._log.critical(
                "Unable to apply schema: {error}", sql=sql, error=e
            )
            raise StorageError(f"Unable to apply schema: {e}")
