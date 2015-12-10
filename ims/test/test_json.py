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
    Incident, ReportEntry, Ranger,
    Location, TextOnlyAddress, RodGarettAddress,
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

    def test_datetimeAsRFC3339Naive(self):
        """
        L{datetime_as_rfc3339} returns a proper RFC 3339 string for the given
        naive L{DateTime}, which is assumed to be UTC.
        """
        self.assertRaises(
            ValueError,
            datetime_as_rfc3339, DateTime(1971, 4, 20, 16, 20, 4, tzinfo=None)
        )


    def test_datetimeAsRFC3339UTC(self):
        """
        L{datetime_as_rfc3339} returns a proper RFC 3339 string for the given
        UTC L{DateTime}.
        """
        self.assertEquals(
            datetime_as_rfc3339(DateTime(1971, 4, 20, 16, 20, 4, tzinfo=utc)),
            "1971-04-20T16:20:04Z"
        )


    def test_datetimeAsRFC3339Other(self):
        """
        L{datetime_as_rfc3339} returns a proper RFC 3339 string for the given
        non-UTC L{DateTime}.
        """
        tz = FixedOffsetTimeZone.fromSignHoursMinutes("+", 4, 20)

        self.assertEquals(
            datetime_as_rfc3339(DateTime(1971, 4, 20, 20, 40, 4, tzinfo=tz)),
            "1971-04-20T16:20:04Z"
        )


    def test_rfc3339AsDatetime(self):
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

    def test_numberArgumentRequired(self):
        """
        Raise L{TypeError} if passed-in C{number} is C{None}.
        """
        self.assertRaises(
            TypeError,
            incident_from_json, {}, number=None, validate=False,
        )


    def test_jsonMustBeDict(self):
        """
        Raise L{InvalidDataError} if passed-in JSON C{root} is not a C{dict}.
        """
        self.assertRaises(
            InvalidDataError,
            incident_from_json, u"", number=1, validate=False,
        )


    def test_jsonUnknownKeys(self):
        """
        Raise L{InvalidDataError} if JSON data contains an unknown top-level
        key.
        """
        self.assertRaises(
            InvalidDataError,
            incident_from_json, {u"xyzzy": u"foo"}, number=1, validate=False,
        )


    def incidentWithJSONStuff(attributes):
        """
        Make a new incident object with incident number C{1}, and the specified
        additional attributes.  The incident is not validated.
        """
        json = dict(number=1)
        json.update(attributes)
        incident_from_json(json, number=1, validate=False)


    def test_incidentFromJSONEmpty(self):
        """
        Deserializing from empty JSON data produces an almost-empty incident;
        only the incident number is inserted.
        """
        incident = incident_from_json({}, number=1, validate=False)
        self.assertEquals(incident, Incident(number=1))


    def test_incidentFromJSONNumber(self):
        """
        Deserialize an incident number from JSON data.
        """
        incident = incident_from_json(
            {JSON.incident_number.value: 1}, number=1, validate=False
        )
        self.assertEquals(incident.number, 1)


    def test_incidentFromJSONNumberMissing(self):
        """
        Deserializing without an incident number from JSON data uses the number
        passed in as an argument.
        """
        incident = incident_from_json({}, number=1, validate=False)
        self.assertEquals(incident.number, 1)


    def test_incidentFromJSONNumberWrong(self):
        """
        Deserializing a incident number from JSON data while providing a
        different incident number as an argument raises L{InvalidDataError}.
        """
        self.assertRaises(
            InvalidDataError,
            incident_from_json, {JSON.incident_number.value: 1}, number=2
        )


    def test_incidentFromJSONPriority(self):
        """
        Deserialize an incident priority from JSON data.
        """
        incident = incident_from_json(
            {
                JSON.incident_number.value: 1,
                JSON.incident_priority.value: 2,
            },
            number=1, validate=False
        )
        self.assertEquals(incident.priority, 2)


    def test_incidentFromJSONSummary(self):
        """
        Deserialize an incident summary from JSON data.
        """
        incident = incident_from_json(
            {
                JSON.incident_number.value: 1,
                JSON.incident_summary.value: u"A B C",
            },
            number=1, validate=False
        )
        self.assertEquals(incident.summary, u"A B C")


    def test_incidentFromJSONTextOnlyLocation(self):
        """
        Deserialize a text only location from JSON data.
        """
        incident = incident_from_json(
            {
                JSON.incident_number.value: 1,
                JSON.incident_location.value: {
                    JSON.location_type.value: JSON.location_type_text.value,
                    JSON.location_name.value: u"Ranger Outpost Zero",
                    JSON.location_garett_description.value: (
                        u"Halfway between the Man and the Temple"
                    ),
                },
            },
            number=1, validate=False
        )
        self.assertEquals(
            incident.location,
            Location(
                name=u"Ranger Outpost Zero",
                address=TextOnlyAddress(
                    description=u"Halfway between the Man and the Temple",
                ),
            )
        )


    def test_incidentFromJSONTextOnlyLocationNoneDescription(self):
        """
        Deserialize a text only location from JSON data with C{None}
        description.
        """
        incident = incident_from_json(
            {
                JSON.incident_number.value: 1,
                JSON.incident_location.value: {
                    JSON.location_type.value: JSON.location_type_text.value,
                    JSON.location_name.value: u"Ranger Outpost Zero",
                    JSON.location_garett_description.value: None,
                },
            },
            number=1, validate=False
        )
        self.assertEquals(
            incident.location,
            Location(name=u"Ranger Outpost Zero", address=None)
        )


    def test_incidentFromJSONGarettLocation(self):
        """
        Deserialize a Rod Garett location from JSON data.
        """
        incident = incident_from_json(
            {
                JSON.incident_number.value: 1,
                JSON.incident_location.value: {
                    JSON.location_type.value: JSON.location_type_garett.value,
                    JSON.location_name.value: u"Tokyo",
                    JSON.location_garett_concentric.value: 3,  # 3 == C
                    JSON.location_garett_radial_hour.value: 9,
                    JSON.location_garett_radial_minute.value: 0,
                    JSON.location_garett_description.value: u"Opposite ESD",
                },
            },
            number=1, validate=False
        )
        self.assertEquals(
            incident.location,
            Location(
                name=u"Tokyo",
                address=RodGarettAddress(
                    concentric=3, radialHour=9, radialMinute=0,
                    description=u"Opposite ESD",
                ),
            )
        )


    def test_incidentFromJSONGarettLocationNoneValues(self):
        """
        Deserialize a Rod Garett location from JSON data with C{None} values.
        """
        incident = incident_from_json(
            {
                JSON.incident_number.value: 1,
                JSON.incident_location.value: {
                    JSON.location_type.value: JSON.location_type_garett.value,
                    JSON.location_name.value: u"Tokyo",
                    JSON.location_garett_concentric.value: None,
                    JSON.location_garett_radial_hour.value: None,
                    JSON.location_garett_radial_minute.value: None,
                    JSON.location_garett_description.value: None,
                },
            },
            number=1, validate=False
        )
        self.assertEquals(
            incident.location,
            Location(name=u"Tokyo", address=None)
        )


    def test_incidentFromJSONLegacyLocation(self):
        """
        Deserialize a location from pre-2015 JSON data.
        """
        incident = incident_from_json(
            {
                JSON.incident_number.value: 1,
                JSON._location_name.value: u"Tokyo",
                JSON._location_address.value: u"9:00 & C",
            },
            number=1, validate=False
        )
        self.assertEquals(
            incident.location,
            Location(name=u"Tokyo", address=TextOnlyAddress(u"9:00 & C"))
        )


    def test_incidentFromJSONLegacyLocationNoneValues(self):
        """
        Deserialize a location from pre-2015 JSON data with C{None} name and/or
        address.
        """
        incident = incident_from_json(
            {
                JSON.incident_number.value: 1,
                JSON._location_name.value: None,
                JSON._location_address.value: None,
            },
            number=1, validate=False
        )
        self.assertEquals(incident.location, None)


    def test_incidentFromJSONLocationMissing(self):
        """
        Deserialize from JSON data with no location.
        """
        incident = incident_from_json(
            {JSON.incident_number.value: 1},
            number=1, validate=False
        )
        self.assertEquals(incident.location, None)


    def test_incidentFromJSONRangers(self):
        """
        Deserialize Rangers from JSON data.
        """
        incident = incident_from_json(
            {
                JSON.incident_number.value: 1,
                JSON.ranger_handles.value: (u"Tool", u"Tulsa"),
            },
            number=1, validate=False
        )
        self.assertEquals(
            incident.rangers,
            frozenset((
                Ranger(u"Tool", None, None),
                Ranger(u"Tulsa", None, None),
            ))
        )


    def test_incidentFromJSONRangersMissing(self):
        """
        Deserialize an incident with no Rangers from JSON data.
        """
        incident = incident_from_json(
            {JSON.incident_number.value: 1},
            number=1, validate=False
        )
        self.assertEquals(incident.rangers, None)


    def test_incidentFromJSONRangersEmpty(self):
        """
        Deserialize an incident with empty Rangers from JSON data.
        """
        incident = incident_from_json(
            {
                JSON.incident_number.value: 1,
                JSON.ranger_handles.value: (),
            },
            number=1, validate=False
        )
        self.assertEquals(incident.rangers, frozenset())


    def test_incidentFromJSONTypes(self):
        """
        Deserialize incident types from JSON data.
        """
        incident = incident_from_json(
            {
                JSON.incident_number.value: 1,
                JSON.incident_types.value: (u"Footsie", u"Jacks"),
            },
            number=1, validate=False
        )
        self.assertEquals(
            incident.incident_types, frozenset((u"Footsie", u"Jacks"))
        )


    def test_incidentFromJSONTypesMissing(self):
        """
        Deserialize an incident with no incident types from JSON data.
        """
        incident = incident_from_json(
            {JSON.incident_number.value: 1},
            number=1, validate=False
        )
        self.assertEquals(incident.incident_types, None)


    def test_incidentFromJSONTypesEmpty(self):
        """
        Deserialize an incident with empty incident types from JSON data.
        """
        incident = incident_from_json(
            {
                JSON.incident_number.value: 1,
                JSON.incident_types.value: (),
            },
            number=1, validate=False
        )
        self.assertEquals(
            incident.incident_types, frozenset()
        )


    def test_incidentFromJSONEntries(self):
        """
        Deserialize report entries from JSON data.
        """
        incident = incident_from_json(
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
            number=1, validate=False
        )
        self.assertEquals(
            incident.report_entries,
            (
                ReportEntry(author=u"Tool", text=u"1 2 3", created=time1),
                ReportEntry(author=u"Tulsa", text=u"A B C", created=time2),
            )
        )


    def test_incidentFromJSONEntriesMissing(self):
        """
        Deserialize an incident with no report entries from JSON data.
        """
        incident = incident_from_json(
            {JSON.incident_number.value: 1},
            number=1, validate=False
        )
        self.assertEquals(incident.report_entries, None)


    def test_incidentFromJSONEntriesEmpty(self):
        """
        Deserialize an incident with empty report entries from JSON data.
        """
        incident = incident_from_json(
            {
                JSON.incident_number.value: 1,
                JSON.report_entries.value: (),
            },
            number=1, validate=False
        )
        self.assertEquals(incident.report_entries, ())


    def test_incidentFromJSONCreated(self):
        """
        Deserialize an incident created time from JSON data.
        """
        incident = incident_from_json(
            {
                JSON.incident_number.value: 1,
                JSON.incident_created.value: datetime_as_rfc3339(time1),
            },
            number=1, validate=False
        )
        self.assertEquals(incident.created, time1)


    def test_incidentFromJSONCreatedMissing(self):
        """
        Deserialize with no incident created time from JSON data.
        """
        incident = incident_from_json(
            {JSON.incident_number.value: 1},
            number=1, validate=False
        )
        self.assertEquals(incident.created, None)


    def test_incidentFromJSONState(self):
        """
        Deserialize an incident created state from JSON data.
        """
        incident = incident_from_json(
            {
                JSON.incident_number.value: 1,
                JSON.incident_state.value: JSON.state_on_scene.value,
            },
            number=1, validate=False
        )
        self.assertEquals(incident.state, IncidentState.on_scene)


    def test_incidentFromJSONStateMissing(self):
        """
        Deserialize with incident state from JSON data.
        """
        incident = incident_from_json(
            {JSON.incident_number.value: 1},
            number=1, validate=False
        )
        self.assertEquals(incident.state, None)


    def test_incidentFromJSONStateLegacy(self):
        """
        Deserialize an incident created state from legacy JSON data.
        """
        for (state, json_key) in (
            (IncidentState.new, JSON._created.value),
            (IncidentState.dispatched, JSON._dispatched.value),
            (IncidentState.on_scene, JSON._on_scene.value),
            (IncidentState.closed, JSON._closed.value),
        ):
            incident = incident_from_json(
                {
                    JSON.incident_number.value: 1,
                    json_key: "2012-09-01T21:00:00Z",
                },
                number=1, validate=False
            )
            self.assertEquals(incident.state, state)



class IncidentSerializationTests(unittest.TestCase):
    """
    Tests for L{incident_as_json}.
    """

    def test_incidentAsJSONNumber(self):
        """
        Serialize with incident number.
        """
        self.assertEquals(
            {JSON.incident_number.value: 1},
            incident_as_json(Incident(number=1))
        )


    def test_incidentAsJSONPriority(self):
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


    def test_incidentAsJSONSummary(self):
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


    def test_incidentAsJSONLocationWithNoneAddress(self):
        """
        Serialize with a location with a C{None} address.
        """
        self.assertEquals(
            {
                JSON.incident_number.value: 1,
                JSON.incident_location.value: {
                    JSON.location_name.value: u"Tokyo",
                    JSON.location_type.value: JSON.location_type_text.value,
                    JSON.location_text_description.value: None,
                },
            },
            incident_as_json(
                Incident(
                    number=1,
                    location=Location(name=u"Tokyo", address=None),
                )
            )
        )


    def test_incidentAsJSONLocationWithNoneValues(self):
        """
        Serialize with a location with C{None} name and address.
        """
        self.assertEquals(
            {
                JSON.incident_number.value: 1,
                JSON.incident_location.value: {
                    JSON.location_name.value: None,
                    JSON.location_type.value: JSON.location_type_text.value,
                    JSON.location_text_description.value: None,
                },
            },
            incident_as_json(
                Incident(
                    number=1,
                    location=Location(name=None, address=None),
                )
            )
        )


    def test_incidentAsJSONLocationWithTextAddress(self):
        """
        Serialize with a location, with a text-only address.
        """
        self.assertEquals(
            {
                JSON.incident_number.value: 1,
                JSON.incident_location.value: {
                    JSON.location_name.value: u"Ranger Outpost Zero",
                    JSON.location_type.value: JSON.location_type_text.value,
                    JSON.location_text_description.value: (
                        u"Halfway between the Man and the Temple"
                    ),
                },
            },
            incident_as_json(
                Incident(
                    number=1,
                    location=Location(
                        name=u"Ranger Outpost Zero",
                        address=TextOnlyAddress(
                            description=(
                                u"Halfway between the Man and the Temple"
                            )
                        ),
                    ),
                )
            )
        )


    def test_incidentAsJSONLocationWithTextAddressNoneDescription(self):
        """
        Serialize with a location, with a text-only address.
        """
        self.assertEquals(
            {
                JSON.incident_number.value: 1,
                JSON.incident_location.value: {
                    JSON.location_name.value: u"Ranger Outpost Zero",
                    JSON.location_type.value: JSON.location_type_text.value,
                    JSON.location_text_description.value: None,
                },
            },
            incident_as_json(
                Incident(
                    number=1,
                    location=Location(
                        name=u"Ranger Outpost Zero",
                        address=TextOnlyAddress(description=None),
                    ),
                )
            )
        )


    def test_incidentAsJSONLocationWithGarettAddress(self):
        """
        Serialize with a location, with a Rod Garett address.
        """
        self.assertEquals(
            {
                JSON.incident_number.value: 1,
                JSON.incident_location.value: {
                    JSON.location_name.value: u"Tokyo",
                    JSON.location_type.value: JSON.location_type_garett.value,
                    JSON.location_garett_concentric.value: 3,  # 3 == C
                    JSON.location_garett_radial_hour.value: 9,
                    JSON.location_garett_radial_minute.value: 0,
                    JSON.location_garett_description.value: (
                        "Back of 9:00 plaza, opposite Medical"
                    ),
                }
            },
            incident_as_json(
                Incident(
                    number=1,
                    location=Location(
                        name=u"Tokyo",
                        address=RodGarettAddress(
                            concentric=3, radialHour=9, radialMinute=0,
                            description="Back of 9:00 plaza, opposite Medical",
                        ),
                    ),
                )
            )
        )


    def test_incidentAsJSONLocationWithGarettAddressNoneValues(self):
        """
        Serialize with a location, with a Rod Garett address, with C{None}
        address values.
        """
        self.assertEquals(
            {
                JSON.incident_number.value: 1,
                JSON.incident_location.value: {
                    JSON.location_name.value: u"Tokyo",
                    JSON.location_type.value: JSON.location_type_garett.value,
                    JSON.location_garett_concentric.value: None,
                    JSON.location_garett_radial_hour.value: None,
                    JSON.location_garett_radial_minute.value: None,
                    JSON.location_garett_description.value: None,
                }
            },
            incident_as_json(
                Incident(
                    number=1,
                    location=Location(
                        name=u"Tokyo",
                        address=RodGarettAddress(
                            concentric=None,
                            radialHour=None,
                            radialMinute=None,
                            description=None,
                        ),
                    ),
                )
            )
        )


    def test_incidentAsJSONRangers(self):
        """
        Serialize with some Rangers.
        """
        result = incident_as_json(
            Incident(
                number=1,
                rangers=(
                    Ranger(u"Tool", None, None),
                    Ranger(u"Tulsa", None, None),
                ),
            )
        )

        self.assertEquals(
            frozenset(result.keys()),
            frozenset((JSON.incident_number.value, JSON.rangers.value))
        )
        self.assertEquals(result[JSON.incident_number.value], 1)
        self.assertEquals(
            frozenset(result[JSON.rangers.value]),
            frozenset((u"Tool", u"Tulsa"))
        )


    def test_incidentAsJSONRangersEmpty(self):
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


    def test_incidentAsJSONTypes(self):
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


    def test_incidentAsJSONTypesEmpty(self):
        """
        Serialize with no incident types.
        """
        self.assertEquals(
            {
                JSON.incident_number.value: 1,
                JSON.incident_types.value: [],
            },
            incident_as_json(Incident(number=1, incident_types=()))
        )


    def test_incidentAsJSONEntries(self):
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


    def test_incidentAsJSONEntriesEmpty(self):
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


    def test_incidentAsJSONCreated(self):
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


    def test_incidentAsJSONState(self):
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

    def test_rangerAsJSONHandle(self):
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


    def test_rangerAsJSONHandleNameStatus(self):
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

    def test_locationAsJSONName(self):
        """
        Serialize with name.
        """
        self.assertEquals(
            {
                "type": "text",
                "name": u"Ranger Outpost Tokyo",
                "description": None,
            },
            location_as_json(Location(name=u"Ranger Outpost Tokyo"))
        )

    def test_locationAsJSONTextOnlyAddress(self):
        """
        Serialize with address.
        """
        self.assertEquals(
            {
                "type": "text",
                "name": None,
                "description": u"The Temple",
            },
            location_as_json(Location(address=TextOnlyAddress(u"The Temple")))
        )

    # FIXME: more complete testing of location_as_json() is in serialization
    # tests above; move that testing here.
