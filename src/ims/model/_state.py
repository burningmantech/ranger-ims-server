"""
Incident state
"""

from enum import Enum, unique


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
