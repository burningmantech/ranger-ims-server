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
Incident Management System database tooling.
"""

from abc import abstractmethod
from pathlib import Path
from textwrap import dedent
from typing import Iterator, Mapping, Optional, Union

from attr import attrib, attrs
from attr.validators import instance_of

from twisted.logger import Logger

from ._abc import IMSDataStore
from ._exceptions import StorageError


__all__ = ()


ParameterValue = Optional[Union[bytes, str, int, float]]
Parameters = Mapping[str, ParameterValue]

Row = Parameters
Rows = Iterator[Row]



@attrs(frozen=True)
class Query(object):
    description: str = attrib(validator=instance_of(str))
    text: str = attrib(validator=instance_of(str), converter=dedent)



class DatabaseStore(IMSDataStore):
    """
    Incident Management System data store using a managed database.
    """

    schemaVersion = 0
    schemaBasePath = Path(__file__).parent / "schema"
    sqlFileExtension = "sql"


    @classmethod
    def loadSchema(cls, version: Union[int, str] = None) -> str:
        """
        Read the schema file with the given version name.
        """
        if version is None:
            version = cls.schemaVersion

        name = f"{version}.{cls.sqlFileExtension}"
        path = cls.schemaBasePath / name
        return path.read_text()


    @property
    def dbManager(self) -> "DatabaseManager":
        return DatabaseManager(self)


    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close any existing connections to the database.
        """


    @abstractmethod
    async def runQuery(
        self, query: Query, parameters: Optional[Parameters] = None
    ) -> Rows:
        """
        Execute the given query with the given parameters, returning the
        resulting rows.
        """


    @abstractmethod
    async def runOperation(
        self, query: Query, parameters: Optional[Parameters] = None
    ) -> None:
        """
        Execute the given query with the given parameters.
        """


    @abstractmethod
    async def dbSchemaVersion(self) -> int:
        """
        The database's current schema version.
        """


    @abstractmethod
    async def applySchema(self, sql: str) -> None:
        """
        Apply the given schema to the database.
        """


    async def upgradeSchema(self) -> None:
        """
        See :meth:`IMSDataStore.upgradeSchema`.
        """
        if await self.dbManager.upgradeSchema():
            await self.disconnect()



@attrs(frozen=True)
class DatabaseManager(object):
    """
    Generic manager for databases.
    """

    _log = Logger()


    store: DatabaseStore = attrib(validator=instance_of(DatabaseStore))


    async def upgradeSchema(self) -> bool:
        """
        Apply schema updates
        """
        currentVersion = self.store.schemaVersion
        version = await self.store.dbSchemaVersion()

        if version < 0:
            raise StorageError(
                f"No upgrade path from schema version {version}"
            )

        if version == currentVersion:
            # No upgrade needed
            return False

        if version > currentVersion:
            raise StorageError(
                f"Schema version {version} is too new "
                f"(current version is {currentVersion})"
            )

        async def sqlUpgrade(fromVersion: int, toVersion: int) -> None:
            self._log.info(
                "Upgrading database schema from version {fromVersion} to "
                "version {toVersion}",
                fromVersion=fromVersion, toVersion=toVersion,
            )

            if fromVersion == 0:
                fileID = f"{toVersion}"
            else:
                fileID = f"{toVersion}-from-{fromVersion}"

            sql = self.store.loadSchema(version=fileID)
            await self.store.applySchema(sql)

        fromVersion = version

        while fromVersion < currentVersion:
            if fromVersion == 0:
                toVersion = currentVersion
            else:
                toVersion = fromVersion + 1

            await sqlUpgrade(fromVersion, toVersion)
            fromVersion = await self.store.dbSchemaVersion()

            # Make sure the schema version increased from last version
            if fromVersion <= version:
                raise StorageError(
                    f"Schema upgrade did not increase schema version "
                    f"({fromVersion} <= {version})"
                )
            version = fromVersion

        return True
