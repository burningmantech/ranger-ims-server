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
Tests for L{ims.edit}.
"""

from datetime import datetime as DateTime

from ..data import IncidentState, Incident, Ranger, Location
from ..json import datetime_as_rfc3339
from ..edit import edit_incident, EditNotAllowedError

from twisted.trial import unittest



class EditingTests(unittest.TestCase):
    """
    Tests for editing of L{Incident}s.
    """

    def test_edit_number_changed(self):
        """
        Editing of an incident's number is not allowed.
        """
        self.assertRaises(
            EditNotAllowedError,
            edit_incident, Incident(number=1), Incident(number=2), u"Tool"
        )


    def test_edit_priority_none(self):
        """
        Edit incident priority to C{None} is a no-op.
        """
        self.assertEditValueNoop("priority", 2, None)


    def test_edit_priority_same(self):
        """
        Edit incident priority to same value is a no-op.
        """
        self.assertEditValueNoop("priority", 2, 2)


    def test_edit_priority_changed(self):
        """
        Edit incident priority to a new value.
        """
        self.assertEditValueChanged("priority", 2, 4)


    def test_edit_summary_none(self):
        """
        Edit incident summary to C{None} is a no-op.
        """
        self.assertEditValueNoop("summary", u"Hello", None)


    def test_edit_summary_same(self):
        """
        Edit incident summary to same value is a no-op.
        """
        self.assertEditValueNoop("summary", u"Hello", u"Hello")


    def test_edit_summary_changed(self):
        """
        Edit incident summary to a new value.
        """
        self.assertEditValueChanged("summary", u"Hello", u"Goodbye")


    def test_edit_location_noop(self):
        """
        Edit incident location to C{None} is a no-op.
        """
        self.assertEditValueNoop(
            "location",
            Location(u"Tokyo", u"9 & C"), None
        )


    def test_edit_location_noop_name(self):
        """
        Edit incident location name to C{None} is a no-op.
        """
        self.assertEditValueNoop(
            "location",
            Location(u"Tokyo", u"9 & C"), Location(None, u"9 & C")
        )


    def test_edit_location_noop_address(self):
        """
        Edit incident location address to C{None} is a no-op.
        """
        self.assertEditValueNoop(
            "location",
            Location(u"Tokyo", u"9 & C"), Location(u"Tokyo", None)
        )


    def test_edit_location_same(self):
        """
        Edit incident location to same value is a no-op.
        """
        self.assertEditValueNoop(
            "location",
            Location(u"Tokyo", u"9 & C"), Location(u"Tokyo", u"9 & C")
        )


    def test_edit_location_changed_name(self):
        """
        Edit incident location name to a new value.
        """
        (edited, before, after) = self.edit_incident(
            "location",
            Location(u"Tokyo", u"9 & C"),
            Location(u"Berlin", None)
        )

        report_text = u"Changed location name to: Berlin"

        self.assertEquals(edited.location.name, u"Berlin")
        self.assertEquals(edited.location.address, u"9 & C")
        self.assertReportEntryAdded(edited, before, after, report_text)


    def test_edit_location_changed_address(self):
        """
        Edit incident location address to a new value.
        """
        (edited, before, after) = self.edit_incident(
            "location",
            Location(u"Tokyo", u"9 & C"),
            Location(None, u"3 & C")
        )

        report_text = u"Changed location address to: 3 & C"

        self.assertEquals(edited.location.name, u"Tokyo")
        self.assertEquals(edited.location.address, u"3 & C")
        self.assertReportEntryAdded(edited, before, after, report_text)


    def test_edit_location_changed_name_address(self):
        """
        Edit incident location name and address to a new value.
        """
        (edited, before, after) = self.edit_incident(
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
        self.assertReportEntryAdded(edited, before, after, report_text)


    def test_edit_rangers_none(self):
        """
        Edit incident personnel to C{None} is a no-op.
        """
        self.assertEditSetNoop(
            "rangers",
            (Ranger(u"Odwally", None, None), Ranger(u"Tulsa", None, None)),
            None
        )


    def test_edit_rangers_same(self):
        """
        Edit incident personnel to same value is a no-op.
        """
        self.assertEditSetNoop(
            "rangers",
            (Ranger(u"Odwally", None, None), Ranger(u"Tulsa", None, None)),
            (Ranger(u"Odwally", None, None), Ranger(u"Tulsa", None, None))
        )


    def test_edit_rangers_changed(self):
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


    def test_edit_types_none(self):
        """
        Edit incident types to C{None} is a no-op.
        """
        self.assertEditSetNoop("incident_types", (u"A", u"B"), None)


    def test_edit_types_same(self):
        """
        Edit incident types to same value is a no-op.
        """
        self.assertEditSetNoop("incident_types", (u"A", u"B"), (u"A", u"B"))


    def test_edit_types_changed(self):
        """
        Edit incident types to a new value.
        """
        self.assertEditSetChanged(
            "incident_types", (u"A", u"B"), (u"A", u"C"), (u"C",), (u"B",)
        )


    def test_edit_state_follow_none(self):
        """
        If a state timestamp is C{None} and not edited, then no following
        state timestamps may be edited.
        """
        for state in IncidentState.iterconstants():
            original = dict(
                (prior.name, DateTime.utcnow())
                for prior in IncidentState.states_prior_to(state)
            )

            for following in IncidentState.states_following(state):
                self.assertRaises(
                    EditNotAllowedError,
                    edit_incident,
                    Incident(number=1, **original),
                    Incident(number=1, **{following.name: DateTime.utcnow()}),
                    u"Tool"
                )


    def test_edit_state_follow_set(self):
        """
        If a state timestamp is edited and the following state timestamps are
        not edited, the following state timestamps should be set to C{None}.
        """
        for state in IncidentState.iterconstants():
            edited = edit_incident(
                Incident(
                    number=1,
                    created=DateTime.utcnow(),
                    dispatched=DateTime.utcnow(),
                    on_scene=DateTime.utcnow(),
                    closed=DateTime.utcnow(),
                ),
                Incident(number=1, **{state.name: DateTime.utcnow()}),
                u"Tool"
            )

            for state in IncidentState.states_following(state):
                self.assertIdentical(None, getattr(edited, state.name))


    def test_edit_state_changed(self):
        """
        Edit incident created date to a new value.
        """
        for state in IncidentState.iterconstants():
            before = DateTime.utcnow()

            state_attrs = dict(
                (s.name, DateTime.utcnow())
                for s in IncidentState.states_prior_to(state)
            )

            now = DateTime.utcnow()

            edited = edit_incident(
                Incident(number=1, **state_attrs),
                Incident(number=1, **{state.name: now}),
                u"Tool"
            )

            after = DateTime.utcnow()

            report_text = u"Changed {attribute} timestamp to: {value}".format(
                attribute=state.name,
                value=datetime_as_rfc3339(now)
            )

            self.assertChanged(edited, state.name, now)
            self.assertReportEntryAdded(edited, before, after, report_text)


    def assertEditValueNoop(self, attribute, old_value, new_value):
        """
        Assert that the value of an attribute did not change.
        """
        (edited, before, after) = self.edit_incident(
            attribute, old_value, new_value
        )

        self.assertNoop(edited, attribute, old_value)


    def assertEditSetNoop(self, attribute, old_values, new_values):
        """
        Assert that the set of values of an attribute did not change.
        """
        (edited, before, after) = self.edit_incident(
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
        (edited, before, after) = self.edit_incident(
            attribute, old_value, new_value
        )

        report_text = u"Changed {attribute} to: {value}".format(
            attribute=attribute.replace(u"_", u" "),
            value=(new_value if new_value else u"<no value>")
        )

        self.assertChanged(edited, attribute, new_value)
        self.assertReportEntryAdded(edited, before, after, report_text)


    def assertEditSetChanged(
        self, attribute, old_values, new_values, added, removed
    ):
        """
        Assert editing of a set of values of an attribute updates the values
        and adds the expected report entry.
        """
        (edited, before, after) = self.edit_incident(
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
        self.assertReportEntryAdded(edited, before, after, report_text)


    def assertChanged(self, edited, attribute, new):
        """
        Assert that an attribute did change and that a report entry was added.
        """
        # Verify that the edit stuck
        self.assertEquals(new, getattr(edited, attribute))


    def assertReportEntryAdded(self, edited, before, after, report_text):
        # Verify that the expected report entry was added
        self.assertEquals(1, len(edited.report_entries))

        last_entry = edited.report_entries[-1]

        self.assertEquals(u"Tool", last_entry.author)
        self.assertTrue(before < last_entry.created < after)
        self.assertTrue(last_entry.system_entry)
        self.assertEquals(report_text, last_entry.text)


    def edit_incident(self, attribute, old, new):
        before = DateTime.utcnow()

        edited = edit_incident(
            Incident(number=1, **{attribute: old}),
            Incident(number=1, **{attribute: new}),
            u"Tool"
        )

        after = DateTime.utcnow()

        return (edited, before, after)
