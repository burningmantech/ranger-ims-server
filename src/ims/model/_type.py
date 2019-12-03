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

from attr import attrs


__all__ = ()


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class IncidentType(object):
    """
    Incident Type
    """

    name: str
    hidden: bool

    def known(self) -> bool:
        return self.name in knownIncidentTypeNames


admin = IncidentType(name="Admin", hidden=False)
junk = IncidentType(name="Junk", hidden=False)


@unique
class KnownIncidentType(Enum):
    """
    Known incident types

    Incident types are a means to categorize incidents.
    Incident types are generally represented as (arbitrary) strings.
    The incident types enumerated here are those that have some relevance to
    the Incident Management System itself, meaning they are treated specially.
    """

    admin = admin.name
    junk = junk.name


knownIncidentTypeNames = frozenset((kt.value for kt in KnownIncidentType))
