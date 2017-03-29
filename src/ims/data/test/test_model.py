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
Tests for L{ims.data.model}.
"""

from datetime import datetime as DateTime

from twisted.trial import unittest

from ...tz import utcNow
from ..model import (
    InvalidDataError,
    IncidentState,
    Incident,
    ReportEntry,
    Ranger,
    Location,
    # Address,
    TextOnlyAddress,
    RodGarettAddress,
)


__all__ = ()



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
        self.assertEquals(incident.incidentTypes, None)
        self.assertIdentical(incident.summary, None)
        self.assertEquals(incident.reportEntries, None)
        self.assertIdentical(incident.created, None)
        self.assertIdentical(incident.state, None)
        self.assertEquals(incident.priority, None)


    def test_init_sortedEntries(self):
        """
        L{Incident.reportEntries} is sorted.
        """
        r1 = ReportEntry("", "", created=DateTime(1972, 6, 29, 12, 0, 1))
        r2 = ReportEntry("", "", created=DateTime(1972, 6, 29, 12, 0, 2))

        for entries in ((r1, r2), (r2, r1)):
            incident = newIncident(reportEntries=entries)
            self.assertEquals((r1, r2), incident.reportEntries)


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
            "priority={i.priority!r},"
            "summary={i.summary!r},"
            "location={i.location!r},"
            "rangers={i.rangers!r},"
            "incidentTypes={i.incidentTypes!r},"
            "reportEntries={i.reportEntries!r},"
            "created={i.created!r},"
            "state={i.state!r},"
            "version={i.version!r})"
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


    def test_validate_location(self):
        """
        L{Incident.validate} incident with valid location.
        """
        incident = newIncident(
            location=Location(
                name="Name",
                address=TextOnlyAddress("Address"),
            )
        )
        incident.validate()


    def test_validate_locationInvalid(self):
        """
        L{Incident.validate} incident with invalid location.
        """
        incident = newIncident(location=Location(name=0))
        self.assertRaises(InvalidDataError, incident.validate)


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
        incident = newIncident(incidentTypes=("some text",))
        incident.validate()


    def test_validate_types_notText(self):
        """
        L{Incident.validate} of incident with non-str incident types.
        """
        incident = newIncident(incidentTypes=(b"some bytes",))
        self.assertRaises(InvalidDataError, incident.validate)


    def test_validate_summary(self):
        """
        L{Incident.validate} of incident with valid summary.
        """
        incident = newIncident(summary="some text")
        incident.validate()


    def test_validate_summary_notText(self):
        """
        L{Incident.validate} of incident with non-str summary.
        """
        incident = newIncident(summary=b"some bytes")
        self.assertRaises(InvalidDataError, incident.validate)


    def test_validate_reportEntry(self):
        """
        L{Incident.validate} incident with valid report entry.
        """
        incident = newIncident(
            reportEntries=[
                ReportEntry(
                    author="Tool",
                    text="All out of no. 2 pencils. Need air drop stat.",
                    created=DateTime.now(),
                ),
            ]
        )
        incident.validate()


    def test_validate_reportEntryInvalid(self):
        """
        L{Incident.validate} incident with invalid report entry.
        """
        incident = newIncident(
            reportEntries=[
                ReportEntry(author=None, created=utcNow(), text=None)
            ],
        )
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


    def test_validate_created_none(self):
        """
        L{Incident.validate} of incident C{None} created time.
        """
        incident = newIncident(created=None)
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
        incident = newIncident(priority="1")
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
        L{ReportEntry.__init__} with given values.
        """
        dt = utcNow()
        entry = ReportEntry(author="Tool", created=dt, text="xyzzy")

        self.assertEquals(entry.author, "Tool")
        self.assertEquals(entry.text, "xyzzy")
        self.assertTrue(entry.created == dt)
        self.assertIdentical(entry.system_entry, False)


    def test_str(self):
        """
        L{ReportEntry.__str__}
        """
        entry = ReportEntry(
            author="Tool",
            text="Something happened!",
            created=DateTime(1972, 6, 29, 12, 0, 0),
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
            author="Tool",
            text="Something happened!",
            created=DateTime(1972, 6, 29, 12, 0, 0),
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
            author="Tool",
            text="Something happened!",
            created=DateTime(1972, 6, 29, 12, 0, 0),
        )
        entry2 = ReportEntry(
            author="Tool",
            text="Something else happened!",
            created=DateTime(1972, 6, 29, 12, 0, 0),
        )
        self.assertNotEquals(entry1, entry2)


    def test_eq_equal(self):
        """
        L{ReportEntry.__eq__} between equal entries.
        """
        entry1a = ReportEntry(
            author="Tool",
            text="Something happened!",
            created=DateTime(1972, 6, 29, 12, 0, 0),
        )
        entry1b = ReportEntry(
            author="Tool",
            text="Something happened!",
            created=DateTime(1972, 6, 29, 12, 0, 0),
        )
        self.assertEquals(entry1a, entry1a)
        self.assertEquals(entry1a, entry1b)


    def test_eq_other(self):
        """
        L{ReportEntry.__eq__} between entry and other type.
        """
        entry = ReportEntry(
            author="Tool",
            text="Something happened!",
            created=DateTime(1972, 6, 29, 12, 0, 0),
        )
        self.assertNotEquals(entry, object())


    def test_ordering(self):
        """
        L{ReportEntry} implements ordering correctly.
        """
        # Define r2 first so we might notice if sort order is (incorrectly)
        # defined by object id (which seems to be the default in CPython)
        r2 = ReportEntry("", "", created=DateTime(1972, 6, 29, 12, 0, 2))
        r1 = ReportEntry("", "", created=DateTime(1972, 6, 29, 12, 0, 1))
        r3 = ReportEntry("", "", created=DateTime(1972, 6, 29, 12, 0, 3))

        for entries in ((r1, r2, r3), (r3, r2, r1)):
            self.assertEquals(sorted(entries), [r1, r2, r3])


    def test_validate(self):
        """
        L{ReportEntry.validate} of valid entry.
        """
        entry = ReportEntry(
            author="Tool", created=utcNow(), text="Something happened!"
        )
        entry.validate()


    def test_validate_author_none(self):
        """
        L{ReportEntry.validate} of entry with L{None} author.
        """
        entry = ReportEntry(
            author=None, created=utcNow(), text="Something happened!"
        )
        self.assertRaises(InvalidDataError, entry.validate)


    # def test_validate_author_empty(self):
    #     """
    #     L{ReportEntry.validate} of entry with empty author.
    #     """
    #     entry = ReportEntry(author="", text="Something happened!")
    #     self.assertRaises(InvalidDataError, entry.validate)


    def test_validate_author_nonText(self):
        """
        L{ReportEntry.validate} of entry with non-str author.
        """
        entry = ReportEntry(
            author=b"Tool", created=utcNow(), text="Something happened!"
        )
        self.assertRaises(InvalidDataError, entry.validate)


    def test_validate_text(self):
        """
        L{ReportEntry.validate} of entry with valid text.
        """
        entry = ReportEntry(
            author="Tool", created=utcNow(), text="Something happened!"
        )
        entry.validate()


    def test_validate_text_none(self):
        """
        L{ReportEntry.validate} of entry with L{None} text.
        """
        entry = ReportEntry(author="Tool", created=utcNow(), text=None)
        self.assertRaises(InvalidDataError, entry.validate)


    # def test_validate_text_empty(self):
    #     """
    #     L{ReportEntry.validate} of entry with empty text.
    #     """
    #     entry = ReportEntry(author="Tool", text="")
    #     self.assertRaises(InvalidDataError, entry.validate)


    def test_validate_text_nonText(self):
        """
        L{ReportEntry.validate} of entry with non-str text.
        """
        entry = ReportEntry(
            author="", created=utcNow(), text=b"Something happened!"
        )
        self.assertRaises(InvalidDataError, entry.validate)


    def test_validate_created(self):
        """
        L{ReportEntry.validate} of entry with valid created time.
        """
        entry = ReportEntry(author="", text="", created=DateTime.now())
        entry.validate()


    def test_validate_created_nonDateTime(self):
        """
        L{ReportEntry.validate} of entry with non-DateTime created time.
        """
        entry = ReportEntry(author="", text="", created=0)
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
            handle="Tool", name="Wilfredo Sánchez Vega", status="vintage"
        )

        self.assertEquals(ranger.handle, "Tool")
        self.assertEquals(ranger.name, "Wilfredo Sánchez Vega")
        self.assertEquals(ranger.status, "vintage")


    def test_str(self):
        """
        L{Ranger.__str__}
        """
        self.assertEquals(
            str(ranger_tool),
            "Tool (Wilfredo Sánchez Vega)"
        )


    def test_repr(self):
        """
        L{Ranger.__repr__}
        """
        self.assertEquals(
            repr(ranger_tool),
            "Ranger(handle='Tool',name='Wilfredo Sánchez Vega',"
            "status='vintage')"
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
            handle="Tulsa",
            name="Curtis Kline",
            status="vintage",
        )
        ranger1b = Ranger(
            handle="Tulsa",
            name="Curtis Kline",
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


    def test_validate_handle_nonText(self):
        """
        L{Ranger.validate} of Ranger with non-str handle.
        """
        ranger = Ranger(handle=b"Tool", name="", status="")
        self.assertRaises(InvalidDataError, ranger.validate)


    def test_validate_name_nonText(self):
        """
        L{Ranger.validate} of Ranger with non-str name.
        """
        ranger = Ranger(
            handle="Tool", name=b"Wilfredo S\xc3\xa1nchez Vega", status=""
        )
        self.assertRaises(InvalidDataError, ranger.validate)


    def test_validate_status_nonText(self):
        """
        L{Ranger.validate} of Ranger with non-str status.
        """
        ranger = Ranger(
            handle="Tool", name="Wifredo Sánchez Vega", status=b"vintage"
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
        location = Location(name="Name", address="Address")
        self.assertEquals(str(location), "Name (Address)")


    def test_str_withName(self):
        """
        L{Location.__str__} with name and no address.
        """
        location = Location(name="Name")
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
            repr(location_zero),
            (
                "Location("
                "name='Ranger Outpost Zero',"
                "address=TextOnlyAddress("
                "description='Halfway between the Man and the Temple'"
                "))"
            )
        )


    def test_eq_different(self):
        """
        L{Location.__eq__} between two different locations.
        """
        self.assertNotEquals(location_zero, location_man)


    def test_eq_equal(self):
        """
        L{Location.__eq__} between equal locations.
        """
        location1a = Location(
            name="Ranger HQ",
            address="5:45 & Esplanade",
        )
        location1b = Location(
            name="Ranger HQ",
            address="5:45 & Esplanade",
        )

        self.assertEquals(location1a, location1a)
        self.assertEquals(location1a, location1b)


    def test_eq_none(self):
        """
        L{Location.__eq__} between location and C{None}.
        """
        self.assertNotEquals(location_zero, None)
        self.assertEquals(Location(), None)
        self.assertEquals(None, Location())


    def test_eq_other(self):
        """
        L{Location.__eq__} between location and other type.
        """
        self.assertNotEquals(location_zero, object())


    def test_validate(self):
        """
        L{Location.validate} of valid location.
        """
        location_zero.validate()


    def test_validate_name(self):
        """
        L{Location.validate} of location with valid name.
        """
        location = Location(name="Ranger HQ")
        location.validate()


    def test_validate_name_nonText(self):
        """
        L{Location.validate} of location with non-str name.
        """
        location = Location(name=b"Ranger HQ")
        self.assertRaises(InvalidDataError, location.validate)


    def test_validate_address(self):
        """
        L{Location.validate} of location with valid address.
        """
        location = Location(address=address_man)
        location.validate()


    def test_validate_address_nonAddress(self):
        """
        L{Location.validate} of location with non-str address.
        """
        location = Location(address="5:45 & Esplanade")
        self.assertRaises(InvalidDataError, location.validate)



# class AddressTests(unittest.TestCase):
#     """
#     Tests for L{Address}
#     """



class TextOnlyAddressTests(unittest.TestCase):
    """
    Tests for L{TextOnlyAddress}
    """

    def test_init_defaults(self):
        """
        L{TextOnlyAddressTests.__init__} with default values.
        """
        address = TextOnlyAddress()

        self.assertIdentical(address.description, None)


    def test_str_withDescription(self):
        """
        L{TextOnlyAddress.__str__} with description.
        """
        self.assertEquals(str(address_man.description), "The Man")


    def test_str_withoutDescription(self):
        """
        L{TextOnlyAddress.__str__} with no description.
        """
        address = TextOnlyAddress()
        self.assertEquals(str(address), "")


    def test_repr(self):
        """
        L{TextOnlyAddress.__repr__}
        """
        self.assertEquals(
            repr(address_man),
            "TextOnlyAddress(description='The Man')"
        )


    def test_eq_different(self):
        """
        L{TextOnlyAddress.__eq__} between two different addresses.
        """
        self.assertNotEquals(location_zero, location_man)


    def test_eq_equal(self):
        """
        L{Location.__eq__} between equal addresses.
        """
        address1a = TextOnlyAddress("12:00 at the fence")
        address1b = TextOnlyAddress("12:00 at the fence")

        self.assertEquals(address1a, address1b)
        self.assertEquals(address1b, address1a)


    def test_eq_none(self):
        """
        L{Location.__eq__} between address and C{None}.
        """
        self.assertNotEquals(address_zero, None)
        self.assertEquals(TextOnlyAddress(), None)
        self.assertEquals(None, TextOnlyAddress())


    def test_eq_other(self):
        """
        L{Location.__eq__} between address and other type.
        """
        self.assertNotEquals(address_man, object())



def newIncident(
    number=1,
    priority=5,
    summary=None,
    location=None,
    rangers=(),
    incidentTypes=(),
    reportEntries=(),
    created=DateTime(2006, 4, 5, 16, 30, 0),
    state=None,
):
    return Incident(
        number,
        priority=priority,
        summary=summary,
        location=location,
        rangers=rangers,
        incidentTypes=incidentTypes,
        reportEntries=reportEntries,
        created=created,
        state=state,
    )



ranger_tool = Ranger(
    "Tool", "Wilfredo Sánchez Vega", "vintage"
)

ranger_tulsa = Ranger(
    "Tulsa", "Curtis Kline", "vintage"
)


address_tokyo = RodGarettAddress(
    concentric=3, radialHour=8, radialMinute=55,
    description="Behind 9:00 Plaza, opposite medical.",
)
location_tokyo = Location("Ranger Outpost Tokyo", address_tokyo)

address_man = TextOnlyAddress("The Man")
location_man = Location("The Man", address_man)

address_zero = TextOnlyAddress("Halfway between the Man and the Temple")
location_zero = Location("Ranger Outpost Zero", address_zero)
