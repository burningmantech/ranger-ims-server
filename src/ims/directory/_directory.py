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
Incident Management System directory service integration.
"""

from abc import ABC, abstractmethod
from typing import NewType, Optional, Sequence


__all__ = ()


IMSUserID = NewType("IMSUserID", str)
IMSGroupID = NewType("IMSGroupID", str)


class IMSUser(ABC):
    """
    IMS user
    """

    @property
    @abstractmethod
    def shortNames(self) -> Sequence[str]:
        """
        Short names (usernames).
        """

    @property
    @abstractmethod
    def active(self) -> bool:
        """
        Whether the user is allowed to log in to the IMS.
        """

    @property
    @abstractmethod
    def uid(self) -> IMSUserID:
        """
        Unique identifier.
        """

    @property
    @abstractmethod
    def groups(self) -> Sequence[IMSGroupID]:
        """
        Groups the user is a member of.
        """

    @abstractmethod
    async def verifyPassword(self, password: str) -> bool:
        """
        Verify whether a password is valid for the user.
        """


class IMSDirectory(ABC):
    """
    IMS directory service.
    """

    async def lookupUser(self, searchTerm: str) -> Optional[IMSUser]:
        """
        Look up a user given a text search term.
        """
