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

from twisted.logger import Logger

from twext.who.idirectory import (
    # DirectoryServiceError, DirectoryAvailabilityError,
    # FieldName as BaseFieldName,
    RecordType as BaseRecordType,
    # IPlaintextPasswordVerifier, DirectoryConfigurationError
)
from twext.who.directory import (
    DirectoryService as BaseDirectoryService,
    DirectoryRecord as BaseDirectoryRecord,
)
from twext.who.expression import (
    MatchExpression,  # ExistsExpression, BooleanExpression,
    # CompoundExpression, Operand, MatchType
)
from twext.who.util import ConstantsContainer



class DirectoryService(BaseDirectoryService):
    """
    Duty Management System directory service.
    """

    log = Logger()

    recordType = ConstantsContainer((
        BaseRecordType.user, BaseRecordType.group,
    ))


    def __init__(self, dms):
        self.dms = dms


    def recordsFromNonCompoundExpression(
        self, expression, recordTypes=None, records=None,
        limitResults=None, timeoutSeconds=None,
    ):
        if isinstance(expression, MatchExpression):
            raise NotImplementedError(
                "Expression: {}".format(expression)
            )

        return BaseDirectoryService.recordsFromNonCompoundExpression(
            expression,
            recordTypes=recordTypes, records=records,
            limitResults=limitResults, timeoutSeconds=timeoutSeconds,
        )


class DirectoryRecord(BaseDirectoryRecord):
    """
    Duty Management System directory record.
    """

    log = Logger()


    # #
    # # Verifiers for twext.who.checker stuff.
    # #

    # def verifyPlaintextPassword(self, password):
    #     return self.service._authenticateUsernamePassword(self.dn, password)
