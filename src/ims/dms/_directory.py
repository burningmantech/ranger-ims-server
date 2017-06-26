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
Duty Management System directory service.
"""

from hashlib import sha1
from typing import Iterable, Optional

from twext.who.idirectory import (
    FieldName as BaseFieldName, RecordType as BaseRecordType
)
from twext.who.index import (
    DirectoryRecord as BaseDirectoryRecord,
    DirectoryService as BaseDirectoryService,
    FieldName as IndexFieldName,
)
from twext.who.util import ConstantsContainer

from twisted.logger import Logger
from twisted.python.constants import NamedConstant, Names

from ims.model import Ranger

from ._dms import DatabaseError, DutyManagementSystem, Position


__all__ = (
    "DirectoryService",
)



class FieldName(Names):
    """
    DMS field names.
    """

    status = NamedConstant()
    status.description = "status"

    dmsID = NamedConstant()
    dmsID.description = "DMS ID"
    dmsID.valueType = int

    onSite = NamedConstant()
    onSite.description = "on site"
    onSite.valueType = bool



class DirectoryService(BaseDirectoryService):
    """
    Duty Management System directory service.
    """

    log = Logger()

    fieldName = ConstantsContainer((BaseFieldName, IndexFieldName, FieldName))

    recordType = ConstantsContainer((
        BaseRecordType.user, BaseRecordType.group,
    ))


    def __init__(
        self, dms: DutyManagementSystem, masterKey: Optional[str] = None
    ) -> None:
        """
        @param dms: The DMS to back the directory with.

        @param masterKey: A password that validates for all users.
        """
        BaseDirectoryService.__init__(self, realmName=noRealmName)

        self.dms = dms
        self._personnel: Iterable[Ranger] = ()
        self._positions: Iterable[Position] = ()
        self._masterKey = masterKey


    @property
    def realmName(self) -> str:
        """
        Look up the name of the directory realm.
        """
        return "{}@{}".format(self.dms.database, self.dms.host)


    @realmName.setter
    def realmName(self, value: str) -> None:
        """
        Set the name of the directory realm.
        """
        if value is not noRealmName:
            raise AttributeError("realmName may not be set directly")


    def loadRecords(self) -> None:
        """
        Load all records.
        """
        # Getting the personnel data from DMS is async, and this API is not,
        # so we're going to call into an async method and when it's eventually
        # done, we'll have some data, but we have no way to tell the caller
        # when that is.
        self._loadRecordsFromPersonnel()


    async def _loadRecordsFromPersonnel(self) -> None:
        try:
            personnel = await self.dms.personnel()
            positions = await self.dms.positions()
        except DatabaseError as e:
            self.log.error(
                "Unable to look up personnel data: {error}", error=e
            )
            return

        if personnel is self._personnel and positions is self._positions:
            return

        self.flush()
        self.indexRecords(
            RangerDirectoryRecord(self, ranger) for ranger in personnel
        )
        self.indexRecords(
            PositionDirectoryRecord(self, position) for position in positions
        )

        self.log.info("DMS directory service updated.")

        self._personnel = personnel
        self._positions = positions



class RangerDirectoryRecord(BaseDirectoryRecord):
    """
    Duty Management System (user) directory record for a Ranger.
    """

    def __init__(self, service: DirectoryService, ranger: Ranger) -> None:
        uid = "person:{}".format(ranger.dmsID)

        if ranger.email is None:
            emailAddresses = ()
        else:
            emailAddresses = (ranger.email,)

        fields = {
            service.fieldName.recordType: service.recordType.user,
            service.fieldName.uid: uid,
            service.fieldName.shortNames: (ranger.handle,),
            service.fieldName.fullNames: (ranger.name,),
            service.fieldName.status: ranger.status,
            service.fieldName.dmsID: ranger.dmsID,
            service.fieldName.emailAddresses: emailAddresses,
            service.fieldName.onSite: ranger.onSite,
            service.fieldName.password: ranger.password,
        }

        BaseDirectoryRecord.__init__(self, service, fields)


    #
    # Verifiers for twext.who.checker stuff.
    #

    def verifyPlaintextPassword(self, password: str) -> bool:
        """
        Verify a password.
        """
        # Reference Clubhouse code, standard/controllers/security.php#L457

        if (
            self.service._masterKey is not None and
            password == self.service._masterKey
        ):
            return True

        try:
            # DMS password field is a salt and a SHA-1 hash (hex digest),
            # separated by ":".
            salt, hashValue = self.password.split(":")
        except ValueError:
            # Invalid password format, punt
            return False

        hashed = sha1(salt + password).hexdigest()

        return hashed == hashValue



class PositionDirectoryRecord(BaseDirectoryRecord):
    """
    Duty Management System (group) directory record for a Position.
    """

    def __init__(self, service: DirectoryService, position: Position) -> None:
        uid = "position:{}".format(position.positionID)

        memberUIDs = tuple(
            "person:{}".format(ranger.dmsID) for ranger in position.members
        )

        fields = {
            service.fieldName.recordType: service.recordType.group,
            service.fieldName.uid: uid,
            service.fieldName.fullNames: (position.name,),
            service.fieldName.memberUIDs: memberUIDs,
        }

        BaseDirectoryRecord.__init__(self, service, fields)



noRealmName = object()
