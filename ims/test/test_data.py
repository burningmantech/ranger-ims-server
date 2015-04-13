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
Tests for L{ims.data}.
"""

from datetime import datetime as DateTime

from twisted.trial import unittest

from ..tz import utcNow
from ..data import (
    InvalidDataError,
    IncidentState,
    Incident,
    ReportEntry,
    Ranger,
    Location,
)



class IncidentStateTests(unittest.TestCase):
    """
    Tests for L{IncidentState}.
    """

    def test_prior(self):
        """
        L{IncidentState.states_prior_to} yields states prior to the given
        state.
        """
        states = tuple(IncidentState.iterconstants())

        for state in states:
            index = states.index(state)

            prior_states = frozenset(IncidentState.states_prior_to(state))

            # Make sure prior_states contains states before index
            self.assertEquals(
                frozenset(states[:index]),
                prior_states
            )

            # Make sure prior_states does not contain states from index
            self.assertEquals(
                frozenset(states[index:]) & prior_states,
                frozenset()
            )


    def test_following(self):
        """
        L{IncidentState.states_following} yields states following the given
        state.
        """
        states = tuple(IncidentState.iterconstants())

        for state in states:
            index = states.index(state) + 1

            following_states = frozenset(IncidentState.states_following(state))

            # Make sure following_states does not contain states before index
            self.assertEquals(
                frozenset(states[:index]) & following_states,
                frozenset()
            )

            # Make sure following_states contains states from index
            self.assertEquals(
                frozenset(states[index:]),
                following_states
            )



class IncidentTests(unittest.TestCase):
    """
    Tests for L{Incident}
    """

    def test_init_defaults(self):
        """
        L{Incident.__init__} with default values.
        """
        incident = Incident(number=1)
        self.assertEquals(incident.number, 1)
        self.assertEquals(incident.rangers, None)
        self.assertIdentical(incident.location, None)
        self.assertEquals(incident.incident_types, None)
        self.assertIdentical(incident.summary, None)
        self.assertEquals(incident.report_entries, None)
        self.assertIdentical(incident.created, None)
        self.assertIdentical(incident.state, None)
        self.assertEquals(incident.priority, None)


    def test_init_numberNotInt(self):
        """
        L{Incident.__init__} with non-int C{number}.
        """
        self.assertRaises(InvalidDataError, Incident, number="1")


    def test_init_numberNotWhole(self):
        """
        L{Incident.__init__} with non-whole C{number}.
        """
        self.assertRaises(InvalidDataError, Incident, number=-1)


    def test_init_sortedEntries(self):
        """
        L{Incident.report_entries} is sorted.
        """
        r1 = ReportEntry(u"", u"", created=DateTime(1972, 06, 29, 12, 0, 1))
        r2 = ReportEntry(u"", u"", created=DateTime(1972, 06, 29, 12, 0, 2))

        for entries in ((r1, r2), (r2, r1)):
            incident = newIncident(report_entries=entries)
            self.assertEquals((r1, r2), incident.report_entries)


    def test_str(self):
        """
        L{Incident.__str__}
        """
        incident = newIncident(summary="Plugh")
        self.assertEquals(str(incident), "1: Plugh")


    def test_str_noneSummary(self):
        """
        L{Incident.__str__}
        """
        incident = newIncident()
        self.assertEquals(str(incident), "1: ")


    def test_repr(self):
        """
        L{Incident.__repr__}
        """
        incident = newIncident()
        self.assertEquals(
            repr(incident),
            "{i.__class__.__name__}("
            "number={i.number!r},"
            "rangers={i.rangers!r},"
            "location={i.location!r},"
            "incident_types={i.incident_types!r},"
            "summary={i.summary!r},"
            "report_entries={i.report_entries!r},"
            "created={i.created!r},"
            "state={i.state!r},"
            "priority={i.priority!r})"
            .format(i=incident)
        )


    def test_eq_different(self):
        """
        L{Incident.__eq__} between two different incidents.
        """
        incident1 = newIncident(summary="a")
        incident2 = newIncident(summary="b")

        self.assertNotEquals(incident1, incident2)


    def test_eq_equal(self):
        """
        L{Incident.__eq__} between equal incidents.
        """
        incident1a = newIncident()
        incident1b = newIncident()

        self.assertEquals(incident1a, incident1a)
        self.assertEquals(incident1a, incident1b)


    def test_eq_other(self):
        """
        L{Incident.__eq__} between incident and another type.
        """
        self.assertNotEquals(newIncident(), object())


    def test_validate(self):
        """
        L{Incident.validate} of valid incident.
        """
        incident = newIncident()
        incident.validate()


    def test_validate_rangers(self):
        """
        L{Incident.validate} of incident with valid Rangers.
        """
        incident = newIncident(rangers=(ranger_tool,))
        incident.validate()


    def test_validate_types(self):
        """
        L{Incident.validate} of incident with valid incident types.
        """
        incident = newIncident(incident_types=(u"some unicode",))
        incident.validate()


    def test_validate_types_notUnicode(self):
        """
        L{Incident.validate} of incident with non-unicode incident types.
        """
        incident = newIncident(incident_types=(b"some bytes",))
        self.assertRaises(InvalidDataError, incident.validate)


    def test_validate_summary(self):
        """
        L{Incident.validate} of incident with valid summary.
        """
        incident = newIncident(summary=u"some unicode")
        incident.validate()


    def test_validate_summary_notUnicode(self):
        """
        L{Incident.validate} of incident with non-unicode summary.
        """
        incident = newIncident(summary=b"some bytes")
        self.assertRaises(InvalidDataError, incident.validate)


    def test_validate_created(self):
        """
        L{Incident.validate} of incident with valid created time.
        """
        incident = newIncident(created=DateTime.now())
        incident.validate()


    def test_validate_created_notDateTime(self):
        """
        L{Incident.validate} of incident with non-DateTime created time.
        """
        incident = newIncident(created=0)
        self.assertRaises(InvalidDataError, incident.validate)


    def test_validate_state(self):
        """
        L{Incident.validate} of incident with valid state.
        """
        incident = newIncident(state=IncidentState.dispatched)
        incident.validate()


    def test_validate_state_invalid(self):
        """
        L{Incident.validate} of incident with invalid state.
        """
        incident = newIncident(state="dispatched")
        self.assertRaises(InvalidDataError, incident.validate)


    def test_validate_priority(self):
        """
        L{Incident.validate} of incident with valid priority.
        """
        incident = newIncident(priority=1)
        incident.validate()


    def test_validate_priority_notInt(self):
        """
        L{Incident.validate} of incident with non-int priority.
        """
        incident = newIncident(priority=u"1")
        self.assertRaises(InvalidDataError, incident.validate)


    def test_validate_priority_outOfBounds(self):
        """
        L{Incident.validate} of incident with out-of-bounds priority.
        """
        incident = newIncident(priority=0)
        self.assertRaises(InvalidDataError, incident.validate)

        incident = newIncident(priority=6)
        self.assertRaises(InvalidDataError, incident.validate)



class ReportEntryTests(unittest.TestCase):
    """
    Tests for L{ReportEntry}
    """

    def test_init_defaults(self):
        """
        L{ReportEntry.__init__} with default values.
        """
        dt1 = utcNow()
        entry = ReportEntry(author=u"Tool", text=u"xyzzy")
        dt2 = utcNow()

        self.assertEquals(entry.author, u"Tool")
        self.assertEquals(entry.text, u"xyzzy")
        self.assertTrue(entry.created >= dt1)
        self.assertTrue(entry.created <= dt2)
        self.assertIdentical(entry.system_entry, False)


    def test_str(self):
        """
        L{ReportEntry.__str__}
        """
        entry = ReportEntry(
            author=u"Tool",
            text=u"Something happened!",
            created=DateTime(1972, 06, 29, 12, 0, 0),
        )
        self.assertEquals(
            str(entry),
            "Tool@1972-06-29 12:00:00: Something happened!"
        )


    def test_repr(self):
        """
        L{ReportEntry.__repr__}
        """
        entry = ReportEntry(
            author=u"Tool",
            text=u"Something happened!",
            created=DateTime(1972, 06, 29, 12, 0, 0),
        )
        self.assertEquals(
            repr(entry),
            "{e.__class__.__name__}("
            "author={e.author!r},"
            "text={e.text!r},"
            "created={e.created!r})"
            .format(e=entry)
        )


    def test_eq_different(self):
        """
        L{ReportEntry.__eq__} between two different entries.
        """
        entry1 = ReportEntry(
            author=u"Tool",
            text=u"Something happened!",
            created=DateTime(1972, 06, 29, 12, 0, 0),
        )
        entry2 = ReportEntry(
            author=u"Tool",
            text=u"Something else happened!",
            created=DateTime(1972, 06, 29, 12, 0, 0),
        )
        self.assertNotEquals(entry1, entry2)


    def test_eq_equal(self):
        """
        L{ReportEntry.__eq__} between equal entries.
        """
        entry1a = ReportEntry(
            author=u"Tool",
            text=u"Something happened!",
            created=DateTime(1972, 06, 29, 12, 0, 0),
        )
        entry1b = ReportEntry(
            author=u"Tool",
            text=u"Something happened!",
            created=DateTime(1972, 06, 29, 12, 0, 0),
        )
        self.assertEquals(entry1a, entry1a)
        self.assertEquals(entry1a, entry1b)


    def test_eq_other(self):
        """
        L{ReportEntry.__eq__} between entry and other type.
        """
        entry = ReportEntry(
            author=u"Tool",
            text=u"Something happened!",
            created=DateTime(1972, 06, 29, 12, 0, 0),
        )
        self.assertNotEquals(entry, object())


    def test_ordering(self):
        """
        L{ReportEntry} implements ordering correctly.
        """
        # Define r2 first so we might notice if sort order is (incorrectly)
        # defined by object id (which seems to be the default in CPython)
        r2 = ReportEntry(u"", u"", created=DateTime(1972, 06, 29, 12, 0, 2))
        r1 = ReportEntry(u"", u"", created=DateTime(1972, 06, 29, 12, 0, 1))
        r3 = ReportEntry(u"", u"", created=DateTime(1972, 06, 29, 12, 0, 3))

        for entries in ((r1, r2, r3), (r3, r2, r1)):
            self.assertEquals(sorted(entries), [r1, r2, r3])


    def test_validate(self):
        """
        L{ReportEntry.validate} of valid entry.
        """
        entry = ReportEntry(author=u"", text=u"")
        entry.validate()


    def test_validate_author(self):
        """
        L{ReportEntry.validate} of entry with valid author.
        """
        entry = ReportEntry(author=u"Tool", text=u"")
        entry.validate()


    def test_validate_author_none(self):
        """
        L{ReportEntry.validate} of entry with L{None} author.
        """
        entry = ReportEntry(author=None, text=u"")
        self.assertRaises(InvalidDataError, entry.validate)


    def test_validate_author_nonUnicode(self):
        """
        L{ReportEntry.validate} of entry with non-unicode author.
        """
        entry = ReportEntry(author=b"Tool", text=u"")
        self.assertRaises(InvalidDataError, entry.validate)


    def test_validate_text(self):
        """
        L{ReportEntry.validate} of entry with valid text.
        """
        entry = ReportEntry(author=u"", text=u"Something happened!")
        entry.validate()


    def test_validate_text_nonUnicode(self):
        """
        L{ReportEntry.validate} of entry with non-unicode text.
        """
        entry = ReportEntry(author=u"", text=b"Something happened!")
        self.assertRaises(InvalidDataError, entry.validate)


    def test_validate_created(self):
        """
        L{ReportEntry.validate} of entry with valid created time.
        """
        entry = ReportEntry(author=u"", text=u"", created=DateTime.now())
        entry.validate()


    def test_validate_created_nonDateTime(self):
        """
        L{ReportEntry.validate} of entry with non-DateTime created time.
        """
        entry = ReportEntry(author=u"", text=u"", created=0)
        self.assertRaises(InvalidDataError, entry.validate)



class RangerTests(unittest.TestCase):
    """
    Tests for L{Ranger}
    """

    def test_init_defaults(self):
        """
        L{Ranger.__init__} with default values.
        """
        ranger = Ranger(
            handle=u"Tool", name=u"Wilfredo S\xe1nchez Vega", status=u"vintage"
        )

        self.assertEquals(ranger.handle, u"Tool")
        self.assertEquals(ranger.name, u"Wilfredo S\xe1nchez Vega")
        self.assertEquals(ranger.status, u"vintage")


    def test_init_noHandle(self):
        """
        L{Ranger.__init__} with no handle.
        """
        self.assertRaises(
            InvalidDataError,
            Ranger,
            handle=u"", name=u"Wilfredo S\xe1nchez Vega", status=u"vintage"
        )


    def test_str(self):
        """
        L{Ranger.__str__}
        """
        self.assertEquals(
            str(ranger_tool),
            "Tool (Wilfredo S\xc3\xa1nchez Vega)"
        )


    def test_repr(self):
        """
        L{Ranger.__repr__}
        """
        self.assertEquals(
            repr(ranger_tool),
            "Ranger(handle=u'Tool',name=u'Wilfredo S\\xe1nchez Vega',"
            "status=u'vintage')"
        )


    def test_eq_different(self):
        """
        L{Ranger.__eq__} between two different entries.
        """
        self.assertNotEquals(ranger_tool, ranger_tulsa)


    def test_eq_equal(self):
        """
        L{Ranger.__eq__} between equal entries.
        """
        ranger1a = Ranger(
            handle=u"Tulsa",
            name=u"Curtis Kline",
            status="vintage",
        )
        ranger1b = Ranger(
            handle=u"Tulsa",
            name=u"Curtis Kline",
            status="vintage",
        )

        self.assertEquals(ranger1a, ranger1a)
        self.assertEquals(ranger1a, ranger1b)


    def test_eq_other(self):
        """
        L{Ranger.__eq__} between ranger and other type.
        """
        self.assertNotEquals(ranger_tool, object())


    def test_validate(self):
        """
        L{Ranger.validate} of valid ranger.
        """
        ranger_tool.validate()


    def test_validate_handle(self):
        """
        L{Ranger.validate} of Ranger with non-unicode handle.
        """
        ranger = Ranger(handle=u"Tool", name=u"", status=u"")
        ranger.validate()


    def test_validate_handle_nonUnicode(self):
        """
        L{Ranger.validate} of Ranger with non-unicode handle.
        """
        ranger = Ranger(handle=b"Tool", name=u"", status=u"")
        self.assertRaises(InvalidDataError, ranger.validate)


    def test_validate_name(self):
        """
        L{Ranger.validate} of Ranger with non-unicode name.
        """
        ranger = Ranger(
            handle=u"Tool", name=u"Wifredo S\xe1nchez Vega", status=u""
        )
        ranger.validate()


    def test_validate_name_nonUnicode(self):
        """
        L{Ranger.validate} of Ranger with non-unicode name.
        """
        ranger = Ranger(
            handle=b"Tool", name=u"Wifredo S\xc3\xa1nchez Vega", status=u""
        )
        self.assertRaises(InvalidDataError, ranger.validate)


    def test_validate_status(self):
        """
        L{Ranger.validate} of Ranger with valid status.
        """
        ranger = Ranger(
            handle=u"Tool", name=u"Wifredo S\xe1nchez Vega", status=u"vintage"
        )
        ranger.validate()


    def test_validate_status_nonUnicode(self):
        """
        L{Ranger.validate} of Ranger with non-unicode status.
        """
        ranger = Ranger(
            handle=b"Tool", name=u"Wifredo S\xc3\xa1nchez Vega",
            status=b"vintage"
        )
        self.assertRaises(InvalidDataError, ranger.validate)



class LocationTests(unittest.TestCase):
    """
    Tests for L{Location}
    """

    def test_init_defaults(self):
        """
        L{Location.__init__} with default values.
        """
        location = Location()

        self.assertIdentical(location.name, None)
        self.assertIdentical(location.address, None)


    def test_str_withNameAndAddress(self):
        """
        L{Location.__str__} with name and address.
        """
        location = Location(name=u"Name", address="Address")
        self.assertEquals(str(location), "Name (Address)")


    def test_str_withName(self):
        """
        L{Location.__str__} with name and no address.
        """
        location = Location(name=u"Name")
        self.assertEquals(str(location), "Name")


    def test_str_withAddress(self):
        """
        L{Location.__str__} with address and no name.
        """
        location = Location(address="Address")
        self.assertEquals(str(location), "(Address)")


    def test_str_withNothin(self):
        """
        L{Location.__str__} with no name or address.
        """
        location = Location()
        self.assertEquals(str(location), "")


    def test_repr(self):
        """
        L{Location.__repr__}
        """
        self.assertEquals(
            repr(location_hq),
            "Location(name=u'Ranger HQ',address=u'5:45 & Esplanade')"
        )


    def test_eq_different(self):
        """
        L{Location.__eq__} between two different entries.
        """
        self.assertNotEquals(location_hq, location_man)


    def test_eq_equal(self):
        """
        L{Location.__eq__} between equal entries.
        """
        location1a = Location(
            name=u"Ranger HQ",
            address=u"5:45 & Esplanade",
        )
        location1b = Location(
            name=u"Ranger HQ",
            address=u"5:45 & Esplanade",
        )

        self.assertEquals(location1a, location1a)
        self.assertEquals(location1a, location1b)


    def test_eq_none(self):
        """
        L{Location.__eq__} between location and None.
        """
        self.assertNotEquals(location_hq, None)
        self.assertEquals(Location(), None)
        self.assertEquals(None, Location())


    def test_eq_other(self):
        """
        L{Location.__eq__} between location and other type.
        """
        self.assertNotEquals(location_hq, object())


    def test_validate(self):
        """
        L{Location.validate} of valid location.
        """
        location_hq.validate()


    def test_validate_name(self):
        """
        L{Location.validate} of location with valid name.
        """
        location = Location(name=u"Ranger HQ")
        location.validate()


    def test_validate_name_nonUnicode(self):
        """
        L{Location.validate} of location with non-unicode name.
        """
        location = Location(name=b"Ranger HQ")
        self.assertRaises(InvalidDataError, location.validate)


    def test_validate_address(self):
        """
        L{Location.validate} of location with valid address.
        """
        location = Location(address=u"5:45 & Esplanade")
        location.validate()


    def test_validate_address_nonUnicode(self):
        """
        L{Location.validate} of location with non-unicode address.
        """
        location = Location(address=b"5:45 & Esplanade")
        self.assertRaises(InvalidDataError, location.validate)



def newIncident(
    number=1,
    priority=5,
    summary=None,
    location=None,
    rangers=(),
    incident_types=(),
    report_entries=(),
    created=None,
    state=None,
):
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



ranger_tool = Ranger(
    u"Tool", u"Wilfredo S\xe1nchez Vega", u"vintage"
)

ranger_tulsa = Ranger(
    u"Tulsa", u"Curtis Kline", u"vintage"
)


location_hq = Location(
    name=u"Ranger HQ",
    address=u"5:45 & Esplanade",
)

location_man = Location(
    name=u"The Man",
    address=u"The Man",
)
