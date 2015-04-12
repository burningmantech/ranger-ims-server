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
Tests for L{ims.json}.
"""

from datetime import datetime as DateTime

from twisted.trial import unittest

from ..data import (
    InvalidDataError, IncidentState,
    Incident, ReportEntry, Ranger, Location,
)
from ..tz import utc, FixedOffsetTimeZone
from ..json import (
    JSON,
    datetime_as_rfc3339, rfc3339_as_datetime,
    incident_from_json, incident_as_json,
    ranger_as_json, location_as_json,
)

from .test_store import time1, time2



class TimeSerializationTests(unittest.TestCase):
    """
    Tests for time serialization and deserialization.
    """

    def test_datetime_as_rfc3339_naive(self):
        """
        L{datetime_as_rfc3339} returns a proper RFC 3339 string for the given
        naive L{DateTime}, which is assumed to be UTC.
        """
        self.assertRaises(
            ValueError,
            datetime_as_rfc3339, DateTime(1971, 4, 20, 16, 20, 4, tzinfo=None)
        )


    def test_datetime_as_rfc3339_utc(self):
        """
        L{datetime_as_rfc3339} returns a proper RFC 3339 string for the given
        UTC L{DateTime}.
        """
        self.assertEquals(
            datetime_as_rfc3339(DateTime(1971, 4, 20, 16, 20, 4, tzinfo=utc)),
            "1971-04-20T16:20:04Z"
        )


    def test_datetime_as_rfc3339_other(self):
        """
        L{datetime_as_rfc3339} returns a proper RFC 3339 string for the given
        non-UTC L{DateTime}.
        """
        tz = FixedOffsetTimeZone.fromSignHoursMinutes("+", 4, 20)

        self.assertEquals(
            datetime_as_rfc3339(DateTime(1971, 4, 20, 20, 40, 4, tzinfo=tz)),
            "1971-04-20T16:20:04Z"
        )


    def test_rfc3339_as_datetime(self):
        """
        L{rfc3339_as_datetime} returns a proper UTC L{DateTime} for the given
        RFC 3339 string.
        """
        self.assertEquals(
            rfc3339_as_datetime("1971-04-20T16:20:04Z"),
            DateTime(1971, 4, 20, 16, 20, 4, tzinfo=utc)
        )



class IncidentDeserializationTests(unittest.TestCase):
    """
    Tests for L{incident_from_json}.
    """

    def test_incident_from_json_number(self):
        """
        Deserialize with incident number.
        """
        self.assertEquals(
            Incident(number=1),
            incident_from_json(
                {JSON.incident_number.value: 1}, number=1, validate=None
            )
        )


    def test_incident_from_json_number_none(self):
        """
        Deserialize without incident number.
        """
        self.assertEquals(
            Incident(number=1),
            incident_from_json({}, number=1, validate=None)
        )


    def test_incident_from_json_number_wrong(self):
        """
        Deserialize with incident number while providing the wrong incident
        number as an argument.
        """
        self.assertRaises(
            InvalidDataError,
            incident_from_json, {JSON.incident_number.value: 1}, number=2
        )


    def test_incident_from_json_priority(self):
        """
        Deserialize with priority.
        """
        self.assertEquals(
            Incident(number=1, priority=2),
            incident_from_json(
                {
                    JSON.incident_number.value: 1,
                    JSON.incident_priority.value: 2,
                },
                number=1, validate=None
            )
        )


    def test_incident_from_json_summary(self):
        """
        Deserialize with summary.
        """
        self.assertEquals(
            Incident(number=1, summary=u"A B C"),
            incident_from_json(
                {
                    JSON.incident_number.value: 1,
                    JSON.incident_summary.value: u"A B C",
                },
                number=1, validate=None
            )
        )


    def test_incident_from_json_location(self):
        """
        Deserialize with location.
        """
        self.assertEquals(
            Incident(
                number=1,
                location=Location(name=u"Tokyo", address=u"9:00 & C"),
            ),
            incident_from_json(
                {
                    JSON.incident_number.value: 1,
                    JSON.location_name.value: u"Tokyo",
                    JSON.location_address.value: u"9:00 & C",
                },
                number=1, validate=None
            )
        )


    def test_incident_from_json_location_none_values(self):
        """
        Deserialize with location with None name and/or address.
        """
        self.assertEquals(
            Incident(
                number=1,
                location=Location(name=None, address=None),
            ),
            incident_from_json(
                {
                    JSON.incident_number.value: 1,
                    JSON.location_name.value: None,
                    JSON.location_address.value: None,
                },
                number=1, validate=None
            )
        )


    def test_incident_from_json_rangers(self):
        """
        Deserialize with some Rangers.
        """
        self.assertEquals(
            Incident(
                number=1,
                rangers=(
                    Ranger(u"Tool", None, None),
                    Ranger(u"Tulsa", None, None),
                ),
            ),
            incident_from_json(
                {
                    JSON.incident_number.value: 1,
                    JSON.ranger_handles.value: (u"Tool", u"Tulsa"),
                },
                number=1, validate=None
            )
        )


    def test_incident_from_json_rangers_empty(self):
        """
        Deserialize with no Rangers.
        """
        self.assertEquals(
            Incident(number=1, rangers=()),
            incident_from_json(
                {
                    JSON.incident_number.value: 1,
                    JSON.ranger_handles.value: (),
                },
                number=1, validate=None
            )
        )


    def test_incident_from_json_types(self):
        """
        Deserialize with some incident types.
        """
        self.assertEquals(
            Incident(
                number=1,
                incident_types=(u"Footsie", u"Jacks"),
            ),
            incident_from_json(
                {
                    JSON.incident_number.value: 1,
                    JSON.incident_types.value: (u"Footsie", u"Jacks"),
                },
                number=1, validate=None
            )
        )


    def test_incident_from_json_types_empty(self):
        """
        Deserialize with no incident types.
        """
        self.assertEquals(
            Incident(number=1, incident_types=()),
            incident_from_json(
                {
                    JSON.incident_number.value: 1,
                    JSON.incident_types.value: (),
                },
                number=1, validate=None
            )
        )


    def test_incident_from_json_entries(self):
        """
        Deserialize with some report entries.
        """
        self.assertEquals(
            Incident(
                number=1,
                report_entries=(
                    ReportEntry(author=u"Tool", text=u"1 2 3", created=time1),
                    ReportEntry(author=u"Tulsa", text=u"A B C", created=time2),
                ),
            ),
            incident_from_json(
                {
                    JSON.incident_number.value: 1,
                    JSON.report_entries.value: (
                        {
                            JSON.entry_author.value: u"Tool",
                            JSON.entry_text.value: u"1 2 3",
                            JSON.entry_created.value: (
                                datetime_as_rfc3339(time1)
                            ),
                        },
                        {
                            JSON.entry_author.value: u"Tulsa",
                            JSON.entry_text.value: u"A B C",
                            JSON.entry_created.value: (
                                datetime_as_rfc3339(time2)
                            ),
                        },
                    ),
                },
                number=1, validate=None
            )
        )


    def test_incident_from_json_entries_empty(self):
        """
        Deserialize with no report entries.
        """
        self.assertEquals(
            Incident(number=1, report_entries=()),
            incident_from_json(
                {
                    JSON.incident_number.value: 1,
                    JSON.report_entries.value: (),
                },
                number=1, validate=None
            )
        )


    def test_incident_from_json_created(self):
        """
        Deserialize with created.
        """
        self.assertEquals(
            Incident(
                number=1,
                created=time1,
            ),
            incident_from_json(
                {
                    JSON.incident_number.value: 1,
                    JSON.incident_created.value: datetime_as_rfc3339(time1),
                },
                number=1, validate=None
            )
        )


    def test_incident_from_json_state(self):
        """
        Deserialize with state.
        """
        self.assertEquals(
            Incident(
                number=1,
                state=IncidentState.on_scene,
            ),
            incident_from_json(
                {
                    JSON.incident_number.value: 1,
                    JSON.incident_state.value: JSON.state_on_scene.value,
                },
                number=1, validate=None
            )
        )


    def test_incident_from_json_state_legacy(self):
        """
        Deserialize with legacy state data.
        """
        for (state, json_key) in (
            (IncidentState.new, JSON._created.value),
            (IncidentState.dispatched, JSON._dispatched.value),
            (IncidentState.on_scene, JSON._on_scene.value),
            (IncidentState.closed, JSON._closed.value),
        ):
            self.assertEquals(
                Incident(number=1, state=state),
                incident_from_json(
                    {
                        JSON.incident_number.value: 1,
                        json_key: time1,
                    },
                    number=1, validate=None
                )
            )



class IncidentSerializationTests(unittest.TestCase):
    """
    Tests for L{incident_as_json}.
    """

    def test_incident_as_json_number(self):
        """
        Serialize with incident number.
        """
        self.assertEquals(
            {JSON.incident_number.value: 1},
            incident_as_json(Incident(number=1))
        )


    def test_incident_as_json_priority(self):
        """
        Serialize with priority.
        """
        self.assertEquals(
            {
                JSON.incident_number.value: 1,
                JSON.incident_priority.value: 2,
            },
            incident_as_json(Incident(number=1, priority=2))
        )


    def test_incident_as_json_summary(self):
        """
        Serialize with summary.
        """
        self.assertEquals(
            {
                JSON.incident_number.value: 1,
                JSON.incident_summary.value: u"A B C",
            },
            incident_as_json(Incident(number=1, summary=u"A B C"))
        )


    def test_incident_as_json_location(self):
        """
        Serialize with location.
        """
        self.assertEquals(
            {
                JSON.incident_number.value: 1,
                JSON.location_name.value: u"Tokyo",
                JSON.location_address.value: u"9:00 & C",
            },
            incident_as_json(
                Incident(
                    number=1,
                    location=Location(name=u"Tokyo", address=u"9:00 & C"),
                )
            )
        )


    def test_incident_as_json_location_none_values(self):
        """
        Serialize with location with None name and/or address.
        """
        self.assertEquals(
            {
                JSON.incident_number.value: 1,
                JSON.location_name.value: None,
                JSON.location_address.value: None,
            },
            incident_as_json(
                Incident(
                    number=1,
                    location=Location(name=None, address=None),
                )
            )
        )


    def test_incident_as_json_rangers(self):
        """
        Serialize with some Rangers.
        """
        self.assertEquals(
            {
                JSON.incident_number.value: 1,
                JSON.ranger_handles.value: [u"Tool", u"Tulsa"],
            },
            incident_as_json(
                Incident(
                    number=1,
                    rangers=(
                        Ranger(u"Tool", None, None),
                        Ranger(u"Tulsa", None, None),
                    ),
                )
            )
        )


    def test_incident_as_json_rangers_empty(self):
        """
        Serialize with no Rangers.
        """
        self.assertEquals(
            {
                JSON.incident_number.value: 1,
                JSON.ranger_handles.value: [],
            },
            incident_as_json(Incident(number=1, rangers=()))
        )


    def test_incident_as_json_types(self):
        """
        Serialize with some incident types.
        """
        result = incident_as_json(
            Incident(
                number=1,
                incident_types=(u"Footsie", u"Jacks"),
            )
        )

        self.assertEquals(
            frozenset(result.keys()),
            frozenset((JSON.incident_number.value, JSON.incident_types.value))
        )
        self.assertEquals(result[JSON.incident_number.value], 1)
        self.assertEquals(
            frozenset(result[JSON.incident_types.value]),
            frozenset((u"Footsie", u"Jacks"))
        )


    def test_incident_as_json_types_empty(self):
        """
        Serialize with no incident types.
        """
        self.assertEquals(
            {
                JSON.incident_number.value: 1,
                JSON.incident_types.value: (),
            },
            incident_as_json(Incident(number=1, incident_types=()))
        )


    def test_incident_as_json_entries(self):
        """
        Serialize with some report entries.
        """
        self.assertEquals(
            {
                JSON.incident_number.value: 1,
                JSON.report_entries.value: [
                    {
                        JSON.entry_author.value: u"Tool",
                        JSON.entry_text.value: u"1 2 3",
                        JSON.entry_created.value: datetime_as_rfc3339(time1),
                        JSON.entry_system.value: False,
                    },
                    {
                        JSON.entry_author.value: u"Tulsa",
                        JSON.entry_text.value: u"A B C",
                        JSON.entry_created.value: datetime_as_rfc3339(time2),
                        JSON.entry_system.value: False,
                    },
                ],
            },
            incident_as_json(
                Incident(
                    number=1,
                    report_entries=(
                        ReportEntry(
                            author=u"Tool", text=u"1 2 3", created=time1
                        ),
                        ReportEntry(
                            author=u"Tulsa", text=u"A B C", created=time2
                        ),
                    ),
                )
            )
        )


    def test_incident_as_json_entries_empty(self):
        """
        Serialize with no report entries.
        """
        self.assertEquals(
            {
                JSON.incident_number.value: 1,
                JSON.report_entries.value: [],
            },
            incident_as_json(
                Incident(number=1, report_entries=())
            )
        )


    def test_incident_as_json_created(self):
        """
        Serialize with created.
        """
        self.assertEquals(
            {
                JSON.incident_number.value: 1,
                JSON.incident_created.value: datetime_as_rfc3339(time1),
            },
            incident_as_json(
                Incident(
                    number=1,
                    created=time1,
                )
            )
        )


    def test_incident_as_json_state(self):
        """
        Serialize with state.
        """
        self.assertEquals(
            {
                JSON.incident_number.value: 1,
                JSON.incident_state.value: JSON.state_on_scene.value,
            },
            incident_as_json(
                Incident(
                    number=1,
                    state=IncidentState.on_scene,
                )
            )
        )



class RangerSerializationTests(unittest.TestCase):
    """
    Tests for L{ranger_as_json}.
    """

    def test_ranger_as_json_handle(self):
        """
        Serialize with handle.
        """
        self.assertEquals(
            {
                JSON.ranger_handle.value: u"Tool",
                JSON.ranger_name.value: None,
                JSON.ranger_status.value: None,
            },
            ranger_as_json(Ranger(handle=u"Tool", name=None, status=None))
        )


    def test_ranger_as_json_name_status(self):
        """
        Serialize with handle, name, status.
        """
        self.assertEquals(
            {
                JSON.ranger_handle.value: u"Tool",
                JSON.ranger_name.value: u"Wilfredo S\xe1nchez",
                JSON.ranger_status.value: u"vintage",
            },
            ranger_as_json(Ranger(
                handle=u"Tool", name=u"Wilfredo S\xe1nchez", status=u"vintage"
            ))
        )



class LocationSerializationTests(unittest.TestCase):
    """
    Tests for L{location_as_json}.
    """

    def test_location_as_json_name(self):
        """
        Serialize with name.
        """
        self.assertEquals(
            {
                "name": u"Ranger Outpost Tokyo",
                "address": None,
            },
            location_as_json(Location(name=u"Ranger Outpost Tokyo"))
        )

    def test_location_as_json_address(self):
        """
        Serialize with name.
        """
        self.assertEquals(
            {
                "name": None,
                "address": u"9::00 & C",
            },
            location_as_json(Location(address=u"9::00 & C"))
        )
