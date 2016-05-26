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
Tests for L{ims.data.edit}.
"""

from twisted.trial import unittest

from ...tz import utcNow
from ..model import IncidentState, Incident, Ranger, Location, ReportEntry
from ..edit import editIncident, EditNotAllowedError
from .test_store import time1, time2



class EditingTests(unittest.TestCase):
    """
    Tests for L{ims.service.edit}.
    """

    def test_numberChanged(self):
        """
        Editing of an incident's number is not allowed.
        """
        self.assertRaises(
            EditNotAllowedError,
            editIncident, Incident(number=1), Incident(number=2), u"Tool"
        )


    def test_priorityNone(self):
        """
        Edit incident priority to C{None} is a no-op.
        """
        self.assertEditValueNoop("priority", 2, None)


    def test_prioritySame(self):
        """
        Edit incident priority to same value is a no-op.
        """
        self.assertEditValueNoop("priority", 2, 2)


    def test_priorityChanged(self):
        """
        Edit incident priority to a new value.
        """
        self.assertEditValueChanged("priority", 2, 4)


    def test_summaryNone(self):
        """
        Edit incident summary to C{None} is a no-op.
        """
        self.assertEditValueNoop("summary", u"Hello", None)


    def test_summarySame(self):
        """
        Edit incident summary to same value is a no-op.
        """
        self.assertEditValueNoop("summary", u"Hello", u"Hello")


    def test_summaryChanged(self):
        """
        Edit incident summary to a new value.
        """
        self.assertEditValueChanged("summary", u"Hello", u"Goodbye")


    def test_locationNoop(self):
        """
        Edit incident location to C{None} is a no-op.
        """
        self.assertEditValueNoop(
            "location",
            Location(u"Tokyo", u"9 & C"), None
        )


    def test_locationNoopName(self):
        """
        Edit incident location name to C{None} is a no-op.
        """
        self.assertEditValueNoop(
            "location",
            Location(u"Tokyo", u"9 & C"), Location(None, u"9 & C")
        )


    def test_locationNoopAddress(self):
        """
        Edit incident location address to C{None} is a no-op.
        """
        self.assertEditValueNoop(
            "location",
            Location(u"Tokyo", u"9 & C"), Location(u"Tokyo", None)
        )


    def test_locationSame(self):
        """
        Edit incident location to same value is a no-op.
        """
        self.assertEditValueNoop(
            "location",
            Location(u"Tokyo", u"9 & C"), Location(u"Tokyo", u"9 & C")
        )


    def test_locationChangedName(self):
        """
        Edit incident location name to a new value.
        """
        (edited, before, after) = self.editIncident(
            "location",
            Location(u"Tokyo", u"9 & C"),
            Location(u"Berlin", None)
        )

        report_text = u"Changed location name to: Berlin"

        self.assertEquals(edited.location.name, u"Berlin")
        self.assertEquals(edited.location.address, u"9 & C")
        self.assertSystemReportEntryAdded(edited, before, after, report_text)


    def test_locationChangedAddress(self):
        """
        Edit incident location address to a new value.
        """
        (edited, before, after) = self.editIncident(
            "location",
            Location(u"Tokyo", u"9 & C"),
            Location(None, u"3 & C")
        )

        report_text = u"Changed location address to: 3 & C"

        self.assertEquals(edited.location.name, u"Tokyo")
        self.assertEquals(edited.location.address, u"3 & C")
        self.assertSystemReportEntryAdded(edited, before, after, report_text)


    def test_locationChangedNameAddress(self):
        """
        Edit incident location name and address to a new value.
        """
        (edited, before, after) = self.editIncident(
            "location",
            Location(u"Tokyo", u"9 & C"),
            Location(u"Berlin", u"3 & C")
        )

        report_text = (
            u"Changed location name to: Berlin\n"
            "Changed location address to: 3 & C"
        )

        self.assertEquals(edited.location.name, u"Berlin")
        self.assertEquals(edited.location.address, u"3 & C")
        self.assertSystemReportEntryAdded(edited, before, after, report_text)


    def test_rangersNone(self):
        """
        Edit incident personnel to C{None} is a no-op.
        """
        self.assertEditSetNoop(
            "rangers",
            (Ranger(u"Odwally", None, None), Ranger(u"Tulsa", None, None)),
            None
        )


    def test_rangersSame(self):
        """
        Edit incident personnel to same value is a no-op.
        """
        self.assertEditSetNoop(
            "rangers",
            (Ranger(u"Odwally", None, None), Ranger(u"Tulsa", None, None)),
            (Ranger(u"Odwally", None, None), Ranger(u"Tulsa", None, None))
        )


    def test_rangersChanged(self):
        """
        Edit incident personnel to a new value.
        """
        self.assertEditSetChanged(
            "rangers",
            (Ranger(u"Odwally", None, None), Ranger(u"Tulsa", None, None)),
            (Ranger(u"Odwally", None, None), Ranger(u"Zeitgeist", None, None)),
            (Ranger(u"Zeitgeist", None, None),),
            (Ranger(u"Tulsa", None, None),),
        )


    def test_typesNone(self):
        """
        Edit incident types to C{None} is a no-op.
        """
        self.assertEditSetNoop("incident_types", (u"A", u"B"), None)


    def test_typesSame(self):
        """
        Edit incident types to same value is a no-op.
        """
        self.assertEditSetNoop("incident_types", (u"A", u"B"), (u"A", u"B"))


    def test_typesChanged(self):
        """
        Edit incident types to a new value.
        """
        self.assertEditSetChanged(
            "incident_types", (u"A", u"B"), (u"A", u"C"), (u"C",), (u"B",)
        )


    def test_createdSame(self):
        """
        Edit incident created timestamp to same value is a no-op.
        """
        self.assertEditValueNoop("created", time1, time1)


    def test_createdNoEdit(self):
        """
        Edit incident created timestamp to C{None} is a no-op.
        """
        self.assertEditValueNoop("created", time1, None)


    def test_createdChanged(self):
        """
        Editing incident created timestamp to a new value is ignored.
        """
        self.assertRaises(
            EditNotAllowedError,
            self.editIncident, "created", time1, time2,
        )


    def test_stateSame(self):
        """
        Edit incident state to same value is a no-op.
        """
        self.assertEditValueNoop(
            "state", IncidentState.on_scene, IncidentState.on_scene
        )


    def test_stateChanged(self):
        """
        Edit incident state to a new value.
        """
        (edited, before, after) = self.editIncident(
            "state", IncidentState.dispatched, IncidentState.on_scene
        )

        report_text = u"Changed state to: On Scene"

        self.assertEquals(edited.state, IncidentState.on_scene)
        self.assertSystemReportEntryAdded(edited, before, after, report_text)


    def test_reportEntry(self):
        """
        Edit report entries appends to (and does not replace) existing report
        entries.
        """
        r1 = ReportEntry(u"Splinter", u"Hello!")
        r2 = ReportEntry(u"Tool", u"Bye!")

        (edited, before, after) = (
            self.editIncident("report_entries", [r1], [r2])
        )

        self.assertEquals(2, len(edited.report_entries))

        self.assertEquals(u"Splinter", edited.report_entries[0].author)
        self.assertEquals(u"Hello!", edited.report_entries[0].text)

        self.assertEquals(u"Tool", edited.report_entries[1].author)
        self.assertEquals(u"Bye!", edited.report_entries[1].text)


    def assertEditValueNoop(self, attribute, old_value, new_value):
        """
        Assert that the value of an attribute did not change.
        """
        (edited, before, after) = self.editIncident(
            attribute, old_value, new_value
        )

        self.assertNoop(edited, attribute, old_value)


    def assertEditSetNoop(self, attribute, old_values, new_values):
        """
        Assert that the set of values of an attribute did not change.
        """
        (edited, before, after) = self.editIncident(
            attribute, old_values, new_values
        )

        if old_values is not None:
            old_values = frozenset(old_values)

        self.assertNoop(edited, attribute, old_values)


    def assertNoop(self, edited, attribute, old):
        """
        Assert that an attribute did not change.
        """
        # Value did not change
        self.assertEquals(old, getattr(edited, attribute))

        # No report entry was added
        self.assertEquals(0, len(edited.report_entries))


    def assertEditValueChanged(self, attribute, old_value, new_value):
        """
        Assert editing of the value of an attribute updates the value and adds
        the expected report entry.
        """
        (edited, before, after) = self.editIncident(
            attribute, old_value, new_value
        )

        report_text = u"Changed {attribute} to: {value}".format(
            attribute=attribute.replace(u"_", u" "),
            value=(new_value if new_value else u"<no value>")
        )

        self.assertChanged(edited, attribute, new_value)
        self.assertSystemReportEntryAdded(edited, before, after, report_text)


    def assertEditSetChanged(
        self, attribute, old_values, new_values, added, removed
    ):
        """
        Assert editing of a set of values of an attribute updates the values
        and adds the expected report entry.
        """
        (edited, before, after) = self.editIncident(
            attribute, old_values, new_values
        )

        if new_values is not None:
            new_values = frozenset(new_values)

        report_text = (
            u"Added to {attribute}: {added}\n"
            u"Removed from {attribute}: {removed}"
        ).format(
            attribute=attribute.replace(u"_", u" "),
            added=u", ".join(unicode(x) for x in added),
            removed=u", ".join(unicode(x) for x in removed),
        )

        self.assertChanged(edited, attribute, new_values)
        self.assertSystemReportEntryAdded(edited, before, after, report_text)


    def assertChanged(self, edited, attribute, new):
        """
        Assert that an attribute did change and that a report entry was added.
        """
        # Verify that the edit stuck
        self.assertEquals(new, getattr(edited, attribute))


    def assertSystemReportEntryAdded(self, edited, before, after, report_text):
        """
        Verify that a report entry was added.
        """
        self.assertEquals(1, len(edited.report_entries))

        last_entry = edited.report_entries[-1]

        self.assertEquals(u"Tool", last_entry.author)
        self.assertTrue(before < last_entry.created < after)
        self.assertTrue(last_entry.system_entry)
        self.assertEquals(report_text, last_entry.text)


    def editIncident(self, attribute, old, new):
        before = utcNow()

        edited = editIncident(
            Incident(number=1, **{attribute: old}),
            Incident(number=1, **{attribute: new}),
            u"Tool"
        )

        after = utcNow()

        return (edited, before, after)
