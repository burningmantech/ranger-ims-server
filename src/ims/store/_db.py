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
from typing import Union

from attr import attrib, attrs
from attr.validators import instance_of

from twisted.logger import Logger

from ._abc import IMSDataStore
from ._exceptions import StorageError



class DatabaseStore(IMSDataStore):
    """
    Incident Management System data store using a managed database.
    """

    schemaVersion = 0
    schemaBasePath = Path(__file__).parent
    sqlFileExtension = "sql"


    @classmethod
    def loadSchema(cls, version: Union[int, str] = None) -> str:
        """
        Read the schema file with the given version name.
        """
        if version is None:
            version = cls.schemaVersion

        name = f"schema.{version}.{cls.sqlFileExtension}"
        path = cls.schemaBasePath / name
        return path.read_text()


    @property
    def dbManager(self) -> "DatabaseManager":
        return DatabaseManager(self)


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



@attrs(frozen=True)
class DatabaseManager(object):
    """
    Generic manager for databases.
    """

    _log = Logger()


    store: DatabaseStore = attrib(validator=instance_of(DatabaseStore))


    async def upgradeSchema(self) -> bool:
        currentVersion = self.store.schemaVersion
        version = await self.store.dbSchemaVersion()

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
            sql = self.store.loadSchema(
                version=f"{toVersion}-from-{fromVersion}"
            )
            await self.store.applySchema(sql)

        if version == 1:
            await sqlUpgrade(1, 2)
            version = 2

        if version == currentVersion:
            # Successfully upgraded to the current version
            return True

        raise StorageError(f"No upgrade path from schema version {version}")
