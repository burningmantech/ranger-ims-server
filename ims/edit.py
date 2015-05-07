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

    # Author is required
    if author is None:
        raise EditNotAllowedError("Author may not be None when editing.")

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


    def edit_value(old_value, new_value, name, describe=None):
        """
        Edit a single value.
        """
        if new_value is None:
            # No edit given for this attribute
            return old_value

        if new_value == old_value:
            # The given edit doesn't change the value
            return old_value

        if name == "created" and old_value != new_value:
            # Created time should not change
            raise EditNotAllowedError("Created time may not change.")

        if describe is None:
            describe = lambda x: x

        system_messages.append(
            u"Changed {attribute} to: {value}".format(
                attribute=name.replace(u"_", u" "),
                value=(describe(new_value) if new_value else u"<no value>")
            )
        )

        return new_value


    def edit_attribute_value(attribute, describe=None):
        """
        Edit the single value of an incident attribute.
        """
        old_value, new_value = old_new(attribute)

        return edit_value(old_value, new_value, attribute, describe=describe)


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
    # Set resulting values
    #

    priority = edit_attribute_value("priority")
    summary  = edit_attribute_value("summary")
    created  = edit_attribute_value("created", describe=datetime_as_rfc3339)
    state    = edit_attribute_value("state", describe=IncidentState.describe)

    rangers        = edit_attribute_set("rangers")
    incident_types = edit_attribute_set("incident_types")

    # Location has to be unpacked
    old_location, new_location = old_new("location")

    if old_location is None:
        location = new_location
    elif new_location is None:
        location = old_location
    else:
        location_name = edit_value(
            old_location.name, new_location.name, "location name"
        )
        location_address = edit_value(
            old_location.address, new_location.address, "location address"
        )
        location = Location(location_name, location_address)

    #
    # Add report entries
    #
    report_entries = []

    # First, keep all existing report entries from the original incident.
    if incident.report_entries is not None:
        for report_entry in incident.report_entries:
            report_entries.append(report_entry)

    # Next, add new system report entries
    if system_messages:
        report_entries.append(
            ReportEntry(
                author=author,
                text=u"\n".join(system_messages),
                system_entry=True,
            )
        )

    # Finally, add new user report entries
    if edits.report_entries is not None:
        for report_entry in edits.report_entries:
            report_entries.append(report_entry)


    #
    # Build and return the edited incident.
    #
    return Incident(
        number,
        priority=priority,
        summary=summary,
        location=location,
        rangers=rangers,
        incident_types=incident_types,
        report_entries=report_entries,
        created=created,
        state=state,
    )
