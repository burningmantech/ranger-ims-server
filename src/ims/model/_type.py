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
Incident type
"""

from enum import Enum, unique


__all__ = ()



@unique
class KnownIncidentType(Enum):
    """
    Known incident types

    Incident types are a means to categorize incidents.
    Incident types are generally represented as (arbitrary) strings.
    The incident types enumerated here are those that have some relevance to
    the Incident Management System itself, meaning they are treated specially.
    """

    admin = "Admin"
    junk  = "Junk"


    def __repr__(self) -> str:
        return "{}[{!r}]".format(self.__class__.__name__, self.name)
