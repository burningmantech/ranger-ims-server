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
Incident editing.
"""

from .data import IncidentState, Incident, Location, ReportEntry
from .json import datetime_as_rfc3339



class EditNotAllowedError(Exception):
    """
    Attempted edit is not allowed.
    """



def edit_incident(incident, edits, author):
    """
    Applies edits to an incident and returns the edited incident.

    @param incident: The incident to edit.
    @type incident: L{Incident}

    @param edits: Edits to make to C{incident}.
    @type edits: L{Incident}

    @param author: The author's handle.
    @type author: L{unicode}

    @return: A new incident which reflects C{edits} applied to C{incident}.
    @rtype: L{Incident}
    """

    # Incident number is not editable
    if incident.number != edits.number:
        raise EditNotAllowedError("Incident number may not be edited.")

    number = incident.number
    system_messages = []


    def old_new(attribute):
        """
        Get the old and new values for an attribute.
        """
        old = getattr(incident, attribute)
        new = getattr(edits, attribute)
        return old, new


    def edit_value(old_value, new_value, name):
        """
        Edit a single value.
        """
        if new_value is None:
            # No edit given for this attribute
            return old_value

        if new_value == old_value:
            # The given edit doesn't change the value
            return old_value

        system_messages.append(
            u"Changed {attribute} to: {value}".format(
                attribute=name.replace(u"_", u" "),
                value=(new_value if new_value else u"<no value>")
            )
        )

        return new_value


    def edit_attribute_value(attribute):
        """
        Edit the single value of an incident attribute.
        """
        old_value, new_value = old_new(attribute)

        return edit_value(old_value, new_value, attribute)


    def edit_attribute_set(attribute):
        """
        Edit the set of values of an incident attribute.
        """
        old_values, new_values = old_new(attribute)

        if new_values is None:
            # No edit given for this attribute
            return old_values

        if new_values == old_values:
            # The given edit doesn't change the values
            return old_values

        # Figure out what's different
        unchanged = old_values & new_values
        removed = old_values ^ unchanged
        added = new_values ^ unchanged

        if added:
            system_messages.append(
                u"Added to {attribute}: {values}".format(
                    attribute=attribute.replace(u"_", u" "),
                    values=u", ".join(unicode(x) for x in added)
                )
            )
        if removed:
            system_messages.append(
                u"Removed from {attribute}: {values}".format(
                    attribute=attribute.replace(u"_", u" "),
                    values=u", ".join(unicode(x) for x in removed)
                )
            )

        return new_values


    def edit_timestamp(edit_states):
        """
        Edit the timestamps on state attributes.
        """
        timestamps = {}

        for state in IncidentState.iterconstants():
            if state in edit_states:
                timestamp = getattr(edits, state.value)
                if timestamp is None:
                    timestamp = getattr(incident, state.value)

                timestamps[state] = timestamp
            else:
                timestamps[state] = None

        return timestamps


    #
    # Ensure that if a state is None, that the following states are also None.
    #

    for state in IncidentState.iterconstants():
        old = getattr(incident, state.name)
        new = getattr(edits, state.name)
        if new is None:
            if old is None:
                for following_state in IncidentState.states_following(state):
                    following_old = getattr(incident, following_state.name)
                    following_new = getattr(edits, following_state.name)
                    if following_new is not None and following_old is None:
                        raise EditNotAllowedError(
                            "{following} time may not be edited "
                            "if {prior} was not edited."
                            .format(
                                following=following_state,
                                prior=state
                            )
                        )
        elif new != old:
            system_messages.append(
                u"Changed {state} timestamp to: {value}".format(
                    state=state.name,
                    value=(datetime_as_rfc3339(new) if new else u"<no value>")
                )
            )


    #
    # Set resulting values
    #

    priority = edit_attribute_value("priority")
    summary  = edit_attribute_value("summary")

    old_location, new_location = old_new("location")

    if new_location is None:
        location = old_location
    else:
        location_name = edit_value(
            old_location.name, new_location.name, "location name"
        )
        location_address = edit_value(
            old_location.address, new_location.address, "location address"
        )
        location = Location(location_name, location_address)

    rangers        = edit_attribute_set("rangers")
    incident_types = edit_attribute_set("incident_types")

    # Walk through states in reversed order and if we find an edit for a state,
    # then apply edits to that state and prior states.
    for state in reversed(tuple(IncidentState.iterconstants())):
        state_edit = getattr(edits, state.name)
        if state_edit is not None:
            state_timestamps = edit_timestamp(
                frozenset(IncidentState.states_prior_to(state)) |
                frozenset((state,))
            )
            break
    else:
        # Having found no state edits, this will leave things as they were.
        state_timestamps = edit_timestamp(
            frozenset(IncidentState.iterconstants())
        )


    #
    # Add system report entries, then user report entries
    #
    report_entries = []

    if system_messages:
        report_entries.append(
            ReportEntry(
                author=author,
                text=u"\n".join(system_messages),
                system_entry=True,
            )
        )

    # FIXME: Add user report entries

    return Incident(
        number,
        priority=priority,
        summary=summary,
        location=location,
        rangers=rangers,
        incident_types=incident_types,
        report_entries=report_entries,
        created=state_timestamps[IncidentState.created],
        dispatched=state_timestamps[IncidentState.dispatched],
        on_scene=state_timestamps[IncidentState.on_scene],
        closed=state_timestamps[IncidentState.closed],
    )
