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

from collections import OrderedDict
from collections.abc import Iterable, Sequence

from attrs import field, frozen

from ..ext.attr import sorted_tuple
from ._accessentry import AccessEntry


__all__ = ()


def sortAndFreezeAccessEntries(
    accessEntries: Iterable[AccessEntry],
) -> Sequence[AccessEntry]:
    return sorted_tuple(OrderedDict.fromkeys(accessEntries))


@frozen(kw_only=True)
class EventAccess:
    """
    Event Access

    Contains access control configuration for an event.
    """

    readers: Sequence[AccessEntry] = field(converter=sortAndFreezeAccessEntries)
    writers: Sequence[AccessEntry] = field(converter=sortAndFreezeAccessEntries)
    reporters: Sequence[AccessEntry] = field(converter=sortAndFreezeAccessEntries)
