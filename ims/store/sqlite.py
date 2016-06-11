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

__all__ = [
    "Storage"
]

from sqlite3 import connect, Row as LameRow
from twisted.python.filepath import FilePath



class Storage(object):
    """
    SQLite-backed storage.
    """

    def __init__(self, dbFilePath):
        self.dbFilePath = dbFilePath
        self._db = openDB(dbFilePath, create=True)


    def loadFromFileStore(self, store):
        """
        Load data from a legacy file store
        """
        raise NotImplementedError()


    def events(self):
        """
        Look up all events in this store.
        """
        raise NotImplementedError()


    def incidentNumbersAndETags(self, event):
        """
        Look up all incident numbers and corresponding ETags in the given event.
        """
        raise NotImplementedError()


    def incidentETag(self, event, number):
        """
        Look up the ETag for the incident with the given number in the given
        event.
        """


    def readIncident(self, event, number):
        """
        Look up the incident with the given number in the given event.
        """
        raise NotImplementedError()


    def readers(self):
        return ("*",)


    def writers(self):
        return ()



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



if __name__ == "__main__":
    with createDB() as db:
        printSchema(db)
