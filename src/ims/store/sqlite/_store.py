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

from collections.abc import Callable, Iterable
from pathlib import Path
from sys import stdout
from typing import Any, ClassVar, TextIO, TypeVar, cast

from attrs import field, frozen, mutable
from twisted.logger import Logger

from ims.ext.sqlite import (
    Connection,
    SQLiteError,
    createDB,
    explainQueryPlans,
    openDB,
    printSchema,
)

from .._db import DatabaseStore, Parameters, Queries, Query, Rows
from .._exceptions import StorageError
from ._queries import queries


__all__ = ()


T = TypeVar("T")

query_eventID = "select ID from EVENT where NAME = :eventID"


@frozen(kw_only=True)
class DataStore(DatabaseStore):
    """
    Incident Management System SQLite data store.
    """

    _log: ClassVar[Logger] = Logger()

    schemaVersion: ClassVar[int] = 7
    schemaBasePath: ClassVar[Path] = Path(__file__).parent / "schema"
    sqlFileExtension: ClassVar[str] = "sqlite"

    query: ClassVar[Queries] = queries

    @mutable(kw_only=True, eq=False)
    class _State:
        """
        Internal mutable state for :class:`DataStore`.
        """

        db: Connection | None = field(default=None, init=False)

    dbPath: Path | None
    _state: _State = field(factory=_State, init=False, repr=False)

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

        def queries() -> Iterable[tuple[str, str]]:
            for name in sorted(
                cls.query.__slots__  # type: ignore[attr-defined]
            ):
                query = getattr(cls.query, name)
                if type(getattr(cls.query, name)) is Query:
                    yield (query.text, name)

        with createDB(None, cls.loadSchema()) as db:
            for line in explainQueryPlans(db, queries()):
                print(line, file=out)
                print(file=out)

    @classmethod
    def _dbSchemaVersion(cls, db: Connection) -> int:
        try:
            for row in db.execute(cls.query.schemaVersion.text):
                return cast(int, row["VERSION"])
            raise StorageError("Invalid schema: no version")

        except SQLiteError as e:
            if e.args[0] == "no such table: SCHEMA_INFO":
                return 0

            cls._log.critical(
                "Unable to {description}: {error}",
                description=cls.query.schemaVersion.description,
                error=e,
            )
            raise StorageError(str(e)) from e

    @property
    def _db(self) -> Connection:
        if self._state.db is None:
            try:
                if self.dbPath is None:
                    self._state.db = createDB(None, schema="")
                else:
                    self._state.db = openDB(self.dbPath, schema="")

            except SQLiteError as e:
                self._log.critical(
                    "Unable to open SQLite database {dbPath}: {error}",
                    dbPath=self.dbPath,
                    error=e,
                )
                raise StorageError(
                    f"Unable to open SQLite database {self.dbPath}: {e}"
                ) from e

        return self._state.db

    async def disconnect(self) -> None:
        """
        See :meth:`DatabaseStore.disconnect`.
        """
        if self._state.db is not None:
            self._state.db.close()
            self._state.db = None

    async def runQuery(
        self, query: Query, parameters: Parameters | None = None
    ) -> Rows:
        if parameters is None:
            parameters = {}

        try:
            return self._db.execute(query.text, parameters)

        except SQLiteError as e:
            self._log.critical(
                "Unable to {description}: {error}",
                description=query.description,
                query=query,
                **parameters,
                error=e,
            )
            raise StorageError(str(e)) from e

    async def runOperation(
        self, query: Query, parameters: Parameters | None = None
    ) -> None:
        await self.runQuery(query, parameters)

    async def runInteraction(
        self,
        interaction: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        try:
            with self._db as db:
                return interaction(db.cursor(), *args, **kwargs)
            raise AssertionError("We shouldn't be here")
        except SQLiteError as e:
            self._log.critical(
                "Interaction {interaction} failed: {error}",
                interaction=interaction,
                error=e,
            )
            raise StorageError(str(e)) from e

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
            raise StorageError(f"Unable to apply schema: {e}") from e

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
