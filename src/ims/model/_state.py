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
Incident state
"""

from ims.ext.enum import Enum, enumOrdering, unique


__all__ = ()



@enumOrdering
@unique
class IncidentState(Enum):
    """
    Incident states

    An incident state is used to roughly denote the progress of an incident.
    Generally, the intended incident work flow is:

      * New: an incident is newly created.
      * Dispatched: a responder is dispatched to deal with the incident.
      * On scene: the responder has arrived and is now engaged in the incident.
      * Closed: the incident is resolved.

    An additional state (on hold) denotes that an incident is unresolved and
    should therefore not be closed, but the dispatcher no responder is actively
    engaged at this time for some reason (eg. the dispatcher is waiting on
    something before attempting another response).

    This differs from a new incident in that it is not expected that a
    responder be dispatched until the reason for putting the incident on hold
    no longer applies.
    """

    new        = object()
    onHold     = object()
    dispatched = object()
    onScene    = object()
    closed     = object()


    def __repr__(self) -> str:
        return "{}[{!r}]".format(self.__class__.__name__, self.name)


    def __str__(self) -> str:
        return dict(
            onHold="on hold",
            onScene="on scene",
        ).get(self.name, self.name)
