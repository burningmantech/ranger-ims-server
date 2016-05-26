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

__all__ = [
    "DirectoryService",
]

from hashlib import sha1

from twisted.python.constants import Names, NamedConstant
from twisted.logger import Logger

from twext.who.idirectory import (
    RecordType as BaseRecordType, FieldName as BaseFieldName
)
from twext.who.index import (
    DirectoryService as BaseDirectoryService,
    DirectoryRecord as BaseDirectoryRecord,
)
from twext.who.util import ConstantsContainer



class FieldName(Names):
    """
    DMS field names.
    """
    status = NamedConstant()
    status.description = u"status"

    dmsID = NamedConstant()
    dmsID.description = u"DMS ID"
    dmsID.valueType = int

    onSite = NamedConstant()
    onSite.description = "on site"
    onSite.valueType = bool



class DirectoryService(BaseDirectoryService):
    """
    Duty Management System directory service.
    """

    log = Logger()

    fieldName = ConstantsContainer((BaseFieldName, FieldName))

    recordType = ConstantsContainer((
        BaseRecordType.user, BaseRecordType.group,
    ))


    def __init__(self, dms):
        BaseDirectoryService.__init__(self, realmName=noRealmName)

        self.dms = dms
        self._personnel = None
        self.loadRecords()


    @property
    def realmName(self):
        return "{}@{}".format(self.dms.database, self.dms.host)


    @realmName.setter
    def realmName(self, value):
        if value is not noRealmName:
            raise AttributeError("realmName may not be set directly")


    def loadRecords(self):
        # Getting the personnel data from DMS is async, and this API is not,
        # so we'll set up a callback to get the data when it's available.

        d = self.dms.personnel()
        d.addCallback(self._loadRecordsFromPersonnel)
        d.addErrback(lambda f: self.log.error(
            "Unable to populate directory: {error}", error=f.getErrorMessage()
        ))


    def _loadRecordsFromPersonnel(self, personnel):
        if personnel is self._personnel:
            return

        self.flush()
        self.indexRecords(
            DirectoryRecord(self, ranger) for ranger in personnel
        )

        self._personnel = personnel



class DirectoryRecord(BaseDirectoryRecord):
    """
    Duty Management System directory record.
    """

    def __init__(self, service, ranger):
        if ranger.email is None:
            emailAddresses = ()
        else:
            emailAddresses = (ranger.email,)

        fields = {
            service.fieldName.recordType: service.recordType.user,
            service.fieldName.uid            : ranger.handle,
            service.fieldName.shortNames     : (ranger.handle,),
            service.fieldName.fullNames      : (ranger.name,),
            service.fieldName.status         : ranger.status,
            service.fieldName.dmsID          : ranger.dmsID,
            service.fieldName.emailAddresses : emailAddresses,
            service.fieldName.onSite         : ranger.onSite,
            service.fieldName.password       : ranger.password,
        }

        BaseDirectoryRecord.__init__(self, service, fields)


    #
    # Verifiers for twext.who.checker stuff.
    #

    def verifyPlaintextPassword(self, password):
        # Reference Clubhouse code, standard/controllers/security.php#L457

        try:
            # DMS password field is a salt and a SHA-1 hash (hex digest),
            # separated by ":".
            salt, hashValue = self.password.split(":")
        except ValueError:
            # Invalid password format, punt
            return False

        hashed = sha1(salt + password).hexdigest()

        return hashed == hashValue



noRealmName = object()
