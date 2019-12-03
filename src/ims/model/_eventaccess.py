# -*- test-case-name: ranger-ims-server.model.test.test_eventaccess -*-

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
Event Access
"""

from typing import FrozenSet

from attr import attrib, attrs

from ._convert import freezeStrings


__all__ = ()


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class EventAccess(object):
    """
    Event Access

    Contains access control configuration for an event.
    """

    readers: FrozenSet[str] = attrib(converter=freezeStrings)
    writers: FrozenSet[str] = attrib(converter=freezeStrings)
    reporters: FrozenSet[str] = attrib(converter=freezeStrings)
