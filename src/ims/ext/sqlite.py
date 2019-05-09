# -*- test-case-name: ranger-ims-server.ext.test.test_sqlite -*-
"""
SQLite utilities
"""

from pathlib import Path
from sqlite3 import (
    Connection as BaseConnection, Cursor as BaseCursor, Error as SQLiteError,
    IntegrityError, Row as BaseRow, connect as sqliteConnect,
)
from typing import (
    Any, Callable, Iterable, Mapping, Optional, Tuple, Type, Union, cast
)
from typing.io import TextIO

from attr import attrib, attrs
from attr.validators import instance_of, optional

from twisted.logger import Logger


__all__ = (
    "Connection",
    "Cursor",
    "ParameterValue",
    "Parameters",
    "QueryPlanExplanation",
    "Row",
    "SQLiteError",
    "createDB",
    "explainQueryPlans",
    "openDB",
    "printSchema",
)


CursorFactory = Callable[..., "Cursor"]

ParameterValue = Optional[Union[bytes, str, int, float]]
Parameters = Mapping[str, ParameterValue]

SQLITE_MIN_INT = -2**63     # 64 bits
SQLITE_MAX_INT = 2**63 - 1  # 64 bits



class Row(BaseRow):
    """
    Subclass of :class:`sqlite3.Row` that has a :class:`dict`-like ``get``
    method.
    """

    def get(
        self, key: str, default: Optional[ParameterValue] = None
    ) -> ParameterValue:
        """
        Return the value for the column named `key`.
        Returns :obj:`None` if there is no such column.
        """
        if key in self.keys():
            return self[key]
        else:
            return default



class Cursor(BaseCursor):
    """
    Subclass of :class:`BaseCursor` that adds logging of SQL statements for
    debugging purposes.
    """

    _log = Logger()


    def executescript(self, sql_script: str) -> "Cursor":
        """
        See :meth:`sqlite3.Cursor.executescript`.
        """
        self._log.debug("EXECUTE SCRIPT:\n{script}", script=sql_script)
        return cast("Cursor", super().executescript(sql_script))


    def execute(
        self, sql: str, parameters: Optional[Parameters] = None
    ) -> "Cursor":
        """
        See :meth:`sqlite3.Cursor.execute`.
        """
        if parameters is None:
            parameters = {}
        self._log.debug(
            "EXECUTE: {sql} <- {parameters}", sql=sql, parameters=parameters
        )
        return cast("Cursor", super().execute(sql, parameters))



class Connection(BaseConnection):
    """
    Subclass of :class:`sqlite3.Connection` that adds logging of SQL statements
    for debugging purposes and an improved row type.
    """

    _log = Logger()


    def cursor(
        self, factory: CursorFactory = cast(CursorFactory, Cursor)
    ) -> "Cursor":
        """
        See :meth:`sqlite3.Cursor.cursor`.
        """
        return cast("Cursor", super().cursor(factory=factory))


    def executeAndPrint(
        self, sql: str, parameters: Optional[Parameters] = None
    ) -> None:
        """
        Execute the given SQL and print the results in a table format.
        """
        def emit(row: Iterable) -> None:
            print(" | ".join(str(i) for i in row))

        printHeader = True

        for row in cast(
            Iterable[Row],
            self.execute(sql, cast(Any, parameters))
        ):
            if printHeader:
                emit(row.keys())
                printHeader = False
            emit(cast(Iterable, row))


    def commit(self) -> None:
        """
        See :meth:`sqlite3.Cursor.commit`.
        """
        self._log.debug("COMMIT")
        super().commit()


    def validateConstraints(self) -> None:
        """
        Validate constraints.
        Raise :exc:`IntegrityError` if there is a constraint violation.
        """
        self.validateForeignKeys()


    def validateForeignKeys(self) -> None:
        """
        Validate foreign key constraints.
        Raise :exc:`IntegrityError` if there is a constraint violation.
        """
        valid = True

        for referent, rowid, referred, constraint in (
            self.execute("pragma foreign_key_check")
        ):
            row = self.execute(
                f"select * from {referent} where ROWID=:rowid",
                dict(rowid=rowid)
            ).fetchone()
            self._log.critical(
                "Foreign key constraint {constraint} violated by "
                "table {referent}, row {rowid} to table {referred}\n"
                "Row: {row}",
                referent=referent,
                rowid=rowid,
                referred=referred,
                constraint=constraint,
                row={k: row[k] for k in row.keys()},
            )

            valid = False

        if not valid:
            raise IntegrityError("Foreign key constraints violated")


    def __enter__(self: "Connection") -> "Connection":
        self._log.debug("---------- ENTER ----------")
        super().__enter__()
        return self


    def __exit__(
        self, exc_type: Type[BaseException], exc_val: BaseException,
        exc_tb: Any,
    ) -> bool:
        self._log.debug("---------- EXIT ----------")
        return super().__exit__(exc_type, exc_val, exc_tb)



def connect(path: Optional[Path]) -> Connection:
    """
    Open the database at the given path and configure it.
    """
    if path is None:
        endpoint = ":memory:"
    else:
        endpoint = str(path)

    db = cast(Connection, sqliteConnect(endpoint, factory=Connection))
    db.row_factory = Row
    db.execute("pragma foreign_keys = true")

    return db


def createDB(path: Optional[Path], schema: str) -> Connection:
    """
    Create a new database at the given path.
    """
    db = connect(path)

    db.executescript(schema)
    db.commit()

    return db


def openDB(path: Path, schema: Optional[str] = None) -> Connection:
    """
    Open an SQLite DB with the schema for this application.
    """
    if path.exists():
        return connect(path)

    if schema is not None:
        return createDB(path, schema)

    raise SQLiteError(f"Database does not exist: {path}")


def printSchema(db: Connection, out: TextIO) -> None:
    """
    Print the database schema.
    """
    for (tableName,) in db.execute(
        """
        select NAME from SQLITE_MASTER where TYPE='table' order by NAME;
        """
    ):
        print(f"{tableName}:", file=out)
        for (
            rowNumber, colName, colType, colNotNull, colDefault, colPK
        ) in db.execute(f"pragma table_info('{tableName}');"):
            print(
                "  {n}: {name}({type}){null}{default}{pk}".format(
                    n=rowNumber,
                    name=colName,
                    type=colType,
                    null=" not null" if colNotNull else "",
                    default=f" [{colDefault}]" if colDefault else "",
                    pk=f" *{colPK}" if colPK else "",
                ),
                file=out,
            )



@attrs(frozen=True)
class QueryPlanExplanation(object):
    """
    Container for information about a query plan.
    """

    @attrs(frozen=True)
    class Line(object):
        """
        A line of information about a query plan.
        """

        nestingOrder: Optional[int] = attrib(
            validator=optional(instance_of(int))
        )
        selectFrom: Optional[int] = attrib(
            validator=optional(instance_of(int))
        )
        details: str = attrib(validator=instance_of(str))

        def __str__(self) -> str:
            return f"[{self.nestingOrder},{self.selectFrom}] {self.details}"


    name: str = attrib(validator=instance_of(str))
    query: str = attrib(validator=instance_of(str))
    lines: Tuple[Line] = cast(
        Tuple[Line], attrib(validator=instance_of(tuple))
    )


    def __str__(self) -> str:
        text = [f"{self.name}:", "", "  -- query --", ""]

        text.extend(
            f"    {line}"
            for line in self.query.strip().split("\n")
        )

        if self.lines:
            text.extend(("", "  -- query plan --", ""))
            text.extend(f"    {line}" for line in self.lines)

        return "\n".join(text)



def explainQueryPlans(
    db: Connection, queries: Iterable[Tuple[str, str]]
) -> Iterable[QueryPlanExplanation]:
    """
    Explain query plans for the given queries.
    """
    for query, name in queries:
        params = dict((x, x) for x in range(query.count(":")))  # Dummy params
        try:
            lines: Iterable[QueryPlanExplanation.Line] = tuple(
                QueryPlanExplanation.Line(
                    nestingOrder=nestingOrder,
                    selectFrom=selectFrom,
                    details=details,
                )
                for n, nestingOrder, selectFrom, details in (
                    db.execute(f"explain query plan {query}", params)
                )
            )
        except SQLiteError as e:
            lines = (QueryPlanExplanation.Line(
                nestingOrder=None, selectFrom=None, details=f"{e}",
            ),)

        yield QueryPlanExplanation(name=name, query=query, lines=lines)
