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
from .json import datetimeAsRFC3339

__all__ = [
    "editIncident",
]



class EditNotAllowedError(Exception):
    """
    Attempted edit is not allowed.
    """



def editIncident(incident, edits, author):
    """
    Apply edits to an incident and return the edited incident.

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
    systemMessages = []


    def old_new(attribute):
        """
        Get the old and new values for an attribute.
        """
        old = getattr(incident, attribute)
        new = getattr(edits, attribute)
        return old, new


    def editValue(oldValue, newValue, name, describe=None):
        """
        Edit a single value.
        """
        if newValue is None:
            # No edit given for this attribute
            return oldValue

        if newValue == oldValue:
            # The given edit doesn't change the value
            return oldValue

        if name == "created" and oldValue != newValue:
            # Created time should not change
            raise EditNotAllowedError("Created time may not change.")

        if describe is None:
            describe = lambda x: x

        systemMessages.append(
            u"Changed {attribute} to: {value}".format(
                attribute=name.replace(u"_", u" "),
                value=(describe(newValue) if newValue else u"<no value>")
            )
        )

        return newValue


    def editAttributeValue(attribute, describe=None):
        """
        Edit the single value of an incident attribute.
        """
        oldValue, newValue = old_new(attribute)

        return editValue(oldValue, newValue, attribute, describe=describe)


    def editAttributeSet(attribute):
        """
        Edit the set of values of an incident attribute.
        """
        oldValues, newValues = old_new(attribute)

        if oldValues is None:
            oldValues = frozenset()

        if newValues is None:
            # No edit given for this attribute
            return oldValues

        if newValues == oldValues:
            # The given edit doesn't change the values
            return oldValues

        # Figure out what's different
        unchanged = oldValues & newValues
        removed   = oldValues ^ unchanged
        added     = newValues ^ unchanged

        if added:
            systemMessages.append(
                u"Added to {attribute}: {values}".format(
                    attribute=attribute.replace(u"_", u" "),
                    values=u", ".join(unicode(x) for x in added)
                )
            )
        if removed:
            systemMessages.append(
                u"Removed from {attribute}: {values}".format(
                    attribute=attribute.replace(u"_", u" "),
                    values=u", ".join(unicode(x) for x in removed)
                )
            )

        return newValues


    # def editTimestamp(editStates):
    #     """
    #     Edit the timestamps on state attributes.
    #     """
    #     timestamps = {}

    #     for state in IncidentState.iterconstants():
    #         if state in editStates:
    #             timestamp = getattr(edits, state.value)
    #             if timestamp is None:
    #                 timestamp = getattr(incident, state.value)

    #             timestamps[state] = timestamp
    #         else:
    #             timestamps[state] = None

    #     return timestamps


    #
    # Set resulting values
    #

    priority = editAttributeValue("priority")
    summary  = editAttributeValue("summary")
    created  = editAttributeValue("created", describe=datetimeAsRFC3339)
    state    = editAttributeValue("state", describe=IncidentState.describe)

    rangers       = editAttributeSet("rangers")
    incidentTypes = editAttributeSet("incident_types")

    # Location has to be unpacked
    oldLocation, newLocation = old_new("location")

    if oldLocation is None:
        location = newLocation
    elif newLocation is None:
        location = oldLocation
    else:
        locationName = editValue(
            oldLocation.name, newLocation.name, "location name"
        )
        locationAddress = editValue(
            oldLocation.address, newLocation.address, "location address"
        )
        location = Location(locationName, locationAddress)

    #
    # Add report entries
    #
    reportEntries = []

    # First, keep all existing report entries from the original incident.
    if incident.report_entries is not None:
        for reportEntry in incident.report_entries:
            reportEntries.append(reportEntry)

    # Next, add new system report entries
    if systemMessages:
        reportEntries.append(
            ReportEntry(
                author=author,
                text=u"\n".join(systemMessages),
                system_entry=True,
            )
        )

    # Finally, add new user report entries
    if edits.report_entries is not None:
        for reportEntry in edits.report_entries:
            # Work-around for clients that resubmit the same entry >1 time
            if reportEntry not in reportEntries:
                reportEntries.append(reportEntry)


    #
    # Build and return the edited incident.
    #
    return Incident(
        number,
        priority=priority,
        summary=summary,
        location=location,
        rangers=rangers,
        incident_types=incidentTypes,
        report_entries=reportEntries,
        created=created,
        state=state,
    )
