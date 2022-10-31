"""
Tests for :mod:`ranger-ims-server.ext.sqlite`
"""

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from sqlite3 import Error as SQLiteError
from textwrap import dedent
from typing import Any, cast

from .. import sqlite
from ..sqlite import (
    BaseCursor,
    Connection,
    QueryPlanExplanation,
    connect,
    createDB,
    explainQueryPlans,
    openDB,
    printSchema,
)
from ..trial import TestCase


__all__ = ()


class ConnectionTests(TestCase):
    """
    Tests for :class:`Connection` and related functions.
    """

    def patchConnectionCallable(self, name: str) -> None:
        def _connect(database: Any, *args: Any, **kwargs: Any) -> Connection:
            self.connections.append(database)
            return Connection(":memory:")

        self.connections: list[str] = []
        self.patch(sqlite, name, _connect)

    def test_row_get(self) -> None:
        """
        :meth:`sqlite.Row.get` behaves like :meth:`dict.get`.
        """
        schema = dedent(
            """
            create table PERSON (
                ID   integer not null,
                NAME text    not null,

                primary key (ID),
                unique (NAME)
            );
            insert into PERSON (NAME) values ('John Doe');
            """
        )

        db = createDB(None, schema=schema)

        for row in db.execute("select NAME from PERSON"):
            name = row["NAME"]
            self.assertEqual(row.get("NAME"), name)
            self.assertEqual(row.get("XYZZY", None), None)
            break
        else:
            self.fail("No rows found")

    def test_connect_none(self) -> None:
        """
        :func:`connect` with :obj:`None` argument connects to `:memory:`.
        """
        self.patchConnectionCallable("Connection")

        connect(None)

        self.assertEqual(self.connections, [":memory:"])

    def test_connect_path(self) -> None:
        """
        :func:`connect` with a :class:`Path` argument connects to that path.
        """
        self.patchConnectionCallable("Connection")

        path = Path(__file__)
        connect(path)

        self.assertEqual(self.connections, [str(path)])

    def test_createDB_schema(self) -> None:
        """
        :func:`createDB` creates a DB with the expected schema.
        """
        schema = dedent(
            """
            create table PERSON (
                ID   integer not null,
                NAME text    not null,

                primary key (ID),
                unique (NAME)
            );
            """
        )

        db = createDB(None, schema=schema)

        out = StringIO()
        printSchema(db, out)
        self.assertEqual(
            out.getvalue(),
            dedent(
                """
                PERSON:
                  0: ID(integer) not null *1
                  1: NAME(text) not null
                """[
                    1:
                ]
            ),
        )

    def test_openDB_exists(self) -> None:
        """
        :func:`openDB` with a :class:`Path` argument that exists connects to
        that path.
        """
        self.patchConnectionCallable("connect")

        path = Path(__file__)
        openDB(path)

        self.assertEqual(self.connections, [path])

    def test_openDB_create(self) -> None:
        """
        :func:`openDB` with a :class:`Path` argument that doesn't exist and
        ``create=True`` creates that path.
        """
        self.patchConnectionCallable("createDB")

        path = Path(__file__) / "xyzzy"
        openDB(path, schema="")

        self.assertEqual(self.connections, [path])

    def test_openDB_doesNotExist(self) -> None:
        """
        :func:`openDB` with a :class:`Path` argument that doesn't exist and
        ``create=False`` raises :exc:`SQLiteError`.
        """
        self.patchConnectionCallable("createDB")

        path = Path(__file__) / "xyzzy"

        self.assertRaises(SQLiteError, openDB, path)


class DebugToolsTests(TestCase):
    """
    Tests for :class:`Connection`
    """

    def test_printSchema(self) -> None:
        """
        :func:`printSchema` prints a summary of the schema for the given
        :class:`Connection`.
        """
        raise NotImplementedError()

    test_printSchema.todo = "unimplemented"  # type: ignore[attr-defined]

    def test_explainQueryPlans(self) -> None:
        """
        :func:`explainQueryPlans` ...
        """
        raise NotImplementedError()

    test_explainQueryPlans.todo = "unimplemented"  # type: ignore[attr-defined]

    def test_QueryPlanExplanation_Lines_str(self) -> None:
        """
        :meth:`QueryPlanExplanation.Line.__str__` emits the expected string.
        """
        line = QueryPlanExplanation.Line(
            nestingOrder=12, selectFrom=34, details="Blah blah"
        )
        self.assertEqual(str(line), "[12,34] Blah blah")

    def test_str_withLines(self) -> None:
        """
        :meth:`QueryPlanExplanation.__str__` with lines emits the expected
        string.
        """
        explanation = QueryPlanExplanation(
            name="foo",
            query="select * from FOO",
            lines=(
                QueryPlanExplanation.Line(
                    nestingOrder=0, selectFrom=0, details="X"
                ),
            ),
        )
        self.assertEqual(
            str(explanation),
            (
                "foo:\n\n"
                "  -- query --\n\n"
                "    select * from FOO\n\n"
                "  -- query plan --\n\n"
                "    [0,0] X"
            ),
        )

    def test_str_withoutLines(self) -> None:
        """
        :meth:`QueryPlanExplanation.__str__` without lines emits the expected
        string.
        """
        explanation = QueryPlanExplanation(
            name="foo", query="select * from FOO", lines=()
        )
        self.assertEqual(
            str(explanation),
            ("foo:\n\n" "  -- query --\n\n" "    select * from FOO"),
        )

    def test_explainQueryPlans_error(self) -> None:
        """
        :func:`explainQueryPlans` emits ``[None,None] <excetion text>`` when it
        gets a SQLite error while asking for a query plan.
        """
        patchConnect_errors(self)

        schema = dedent(
            """
            create table PERSON (
                ID   integer not null,
                NAME text    not null,

                primary key (ID),
                unique (NAME)
            );
            insert into PERSON (NAME) values ('John Doe');
            """
        )

        db = cast(ErrneousSQLiteConnection, createDB(None, schema=schema))

        db._generateErrors = True

        explanations = [
            str(x)
            for x in explainQueryPlans(
                db, (("select NAME from PERSON", "Person names"),)
            )
        ]

        self.assertEqual(
            tuple(explanations),
            (
                "Person names:\n\n"
                "  -- query --\n\n"
                "    select NAME from PERSON\n\n"
                "  -- query plan --\n\n"
                "    [None,None] execute()",
            ),
        )


class ErrneousSQLiteConnection(Connection):
    """
    SQLite connection that raises errors for fun and profit.
    """

    _generateErrors = False

    @contextmanager
    def noErrors(self) -> Iterator[None]:
        """
        Context manager that suspends the generation of errors.
        """
        generateErrors = self._generateErrors
        self._generateErrors = False
        yield
        self._generateErrors = generateErrors

    def executescript(self, sql_script: str) -> BaseCursor:
        if self._generateErrors:
            raise SQLiteError("executescript()")
        return super().executescript(sql_script)

    def execute(  # type: ignore[override]
        self, sql: str, parameters: Mapping[str, object] | None = None
    ) -> BaseCursor:
        if parameters is None:
            parameters = {}
        if self._generateErrors:
            raise SQLiteError("execute()")
        return super().execute(sql, parameters)


def patchConnect_errors(testCase: TestCase) -> None:
    """
    Patch :func:`connect` to create :class:`ErrneousSQLiteConnection`s.
    """

    def connect(database: str | None) -> Connection:
        if database is None:
            database = ":memory:"
        db = ErrneousSQLiteConnection(database)
        return db

    testCase.patch(sqlite, "connect", connect)
