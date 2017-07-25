# -*- test-case-name: ranger-ims-server.model.test.test_event -*-

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
Event
"""

from attr import attrib, attrs
from attr.validators import instance_of

from ims.ext.attr import true


__all__ = ()



@attrs(frozen=True)
class Event(object):
    """
    Event

    An event identifies a container for incident data.
    """

    id: str = attrib(validator=true(instance_of(str)))


    def __str__(self) -> str:
        return self.id
