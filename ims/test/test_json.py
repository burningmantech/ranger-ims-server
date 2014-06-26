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

# from cStringIO import StringIO
# from datetime import datetime

from twisted.trial import unittest

from ..data import (
    InvalidDataError,
    Incident, ReportEntry, Ranger, Location,
)
from ..json import (
    JSON,
    datetime_as_rfc3339,
    incident_from_json, incident_as_json,
    ranger_as_json,
)

from .test_store import time1, time2, time3


class ConstantTests(unittest.TestCase):
    """
    Tests for constants in L{ims.json}.
    """

    def test_JSON_states(self):
        """
        L{JSON.states} returns incident state names.
        """
        self.assertEquals(
            set(JSON.states()),
            set(
                (
                    JSON.created,
                    JSON.dispatched,
                    JSON.on_scene,
                    JSON.closed,
                )
            ),
        )


    def test_JSON_states_sorting(self):
        """
        Comparison of states implies the correct order.
        """
        states = list(JSON.states())

        self.assertEquals(states, sorted(reversed(states)))



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
            incident_from_json({JSON.number.value: 1}, number=1, validate=None)
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
            incident_from_json, {JSON.number.value: 1}, number=2
        )


    def test_incident_from_json_priority(self):
        """
        Deserialize with priority.
        """
        self.assertEquals(
            Incident(number=1, priority=2),
            incident_from_json(
                {
                    JSON.number.value: 1,
                    JSON.priority.value: 2,
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
                    JSON.number.value: 1,
                    JSON.summary.value: u"A B C",
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
                    JSON.number.value: 1,
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
                    JSON.number.value: 1,
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
                    JSON.number.value: 1,
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
                    JSON.number.value: 1,
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
                    JSON.number.value: 1,
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
                    JSON.number.value: 1,
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
                    JSON.number.value: 1,
                    JSON.report_entries.value: (
                        {
                            JSON.author.value: u"Tool",
                            JSON.text.value: u"1 2 3",
                            JSON.created.value: datetime_as_rfc3339(time1),
                        },
                        {
                            JSON.author.value: u"Tulsa",
                            JSON.text.value: u"A B C",
                            JSON.created.value: datetime_as_rfc3339(time2),
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
                    JSON.number.value: 1,
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
                created=time1, dispatched=time1, on_scene=time2, closed=time3,
            ),
            incident_from_json(
                {
                    JSON.number.value: 1,
                    JSON.created.value: datetime_as_rfc3339(time1),
                    JSON.dispatched.value: datetime_as_rfc3339(time1),
                    JSON.on_scene.value: datetime_as_rfc3339(time2),
                    JSON.closed.value: datetime_as_rfc3339(time3),
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
            {JSON.number.value: 1},
            incident_as_json(Incident(number=1))
        )


    def test_incident_as_json_priority(self):
        """
        Serialize with priority.
        """
        self.assertEquals(
            {
                JSON.number.value: 1,
                JSON.priority.value: 2,
            },
            incident_as_json(Incident(number=1, priority=2))
        )


    def test_incident_as_json_summary(self):
        """
        Serialize with summary.
        """
        self.assertEquals(
            {
                JSON.number.value: 1,
                JSON.summary.value: u"A B C",
            },
            incident_as_json(Incident(number=1, summary=u"A B C"))
        )


    def test_incident_as_json_location(self):
        """
        Serialize with location.
        """
        self.assertEquals(
            {
                JSON.number.value: 1,
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
                JSON.number.value: 1,
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
                JSON.number.value: 1,
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
                JSON.number.value: 1,
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
            frozenset((JSON.number.value, JSON.incident_types.value))
        )
        self.assertEquals(result[JSON.number.value], 1)
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
                JSON.number.value: 1,
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
                JSON.number.value: 1,
                JSON.report_entries.value: [
                    {
                        JSON.author.value: u"Tool",
                        JSON.text.value: u"1 2 3",
                        JSON.created.value: datetime_as_rfc3339(time1),
                        JSON.system_entry.value: False,
                    },
                    {
                        JSON.author.value: u"Tulsa",
                        JSON.text.value: u"A B C",
                        JSON.created.value: datetime_as_rfc3339(time2),
                        JSON.system_entry.value: False,
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
                JSON.number.value: 1,
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
                JSON.number.value: 1,
                JSON.created.value: datetime_as_rfc3339(time1),
                JSON.dispatched.value: datetime_as_rfc3339(time1),
                JSON.on_scene.value: datetime_as_rfc3339(time2),
                JSON.closed.value: datetime_as_rfc3339(time3),
            },
            incident_as_json(
                Incident(
                    number=1,
                    created=time1,
                    dispatched=time1,
                    on_scene=time2,
                    closed=time3,
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
        Serialize with handle.
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
