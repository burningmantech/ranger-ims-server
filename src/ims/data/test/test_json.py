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
Tests for L{ims.data.json}.
"""

from datetime import datetime as DateTime

from twisted.trial import unittest

from ...tz import utc, FixedOffsetTimeZone
from ...store.test.test_file import time1, time2
from ..model import (
    InvalidDataError, IncidentState,
    Incident, ReportEntry, Ranger,
    Location, TextOnlyAddress, RodGarettAddress,
)
from ..json import (
    JSON,
    dateTimeAsRFC3339Text, rfc3339TextAsDateTime,
    incidentFromJSON, incidentAsJSON, rangerAsJSON, locationAsJSON,
)


__all__ = ()



class TimeSerializationTests(unittest.TestCase):
    """
    Tests for time serialization and deserialization.
    """

    def test_dateTimeAsRFC3339TextNaive(self):
        """
        L{dateTimeAsRFC3339Text} returns a proper RFC 3339 string for the given
        naive L{DateTime}, which is assumed to be UTC.
        """
        self.assertRaises(
            ValueError,
            dateTimeAsRFC3339Text, DateTime(1971, 4, 20, 16, 20, 4, tzinfo=None)
        )


    def test_dateTimeAsRFC3339TextUTC(self):
        """
        L{dateTimeAsRFC3339Text} returns a proper RFC 3339 string for the given
        UTC L{DateTime}.
        """
        self.assertEquals(
            dateTimeAsRFC3339Text(DateTime(1971, 4, 20, 16, 20, 4, tzinfo=utc)),
            "1971-04-20T16:20:04+00:00"
        )


    def test_dateTimeAsRFC3339TextNotUTC(self):
        """
        L{dateTimeAsRFC3339Text} returns a proper RFC 3339 string for the given
        non-UTC L{DateTime}.
        """
        tz = FixedOffsetTimeZone.fromSignHoursMinutes("+", 4, 20)

        self.assertEquals(
            dateTimeAsRFC3339Text(DateTime(1971, 4, 20, 20, 40, 4, tzinfo=tz)),
            "1971-04-20T20:40:04+04:20"
        )


    def test_rfc3339TextAsDateTimeUTCZ(self):
        """
        L{rfc3339TextAsDateTime} returns a proper UTC L{DateTime} for the given
        RFC 3339 string with UTC indicated as C{"Z"}.
        """
        self.assertEquals(
            rfc3339TextAsDateTime("1971-04-20T16:20:04Z"),
            DateTime(1971, 4, 20, 16, 20, 4, tzinfo=utc)
        )


    def test_rfc3339TextAsDateTimeUTCZeroes(self):
        """
        L{rfc3339TextAsDateTime} returns a proper UTC L{DateTime} for the given
        RFC 3339 string with UTC indicated as C{"+00:00"}.
        """
        self.assertEquals(
            rfc3339TextAsDateTime("1971-04-20T16:20:04+00:00"),
            DateTime(1971, 4, 20, 16, 20, 4, tzinfo=utc)
        )



class IncidentDeserializationTests(unittest.TestCase):
    """
    Tests for L{incidentFromJSON}.
    """

    def test_jsonMustBeDict(self):
        """
        Raise L{InvalidDataError} if passed-in JSON C{root} is not a C{dict}.
        """
        self.assertRaises(
            InvalidDataError,
            incidentFromJSON, "", number=1, validate=False,
        )


    def test_jsonUnknownKeys(self):
        """
        Raise L{InvalidDataError} if JSON data contains an unknown top-level
        key.
        """
        self.assertRaises(
            InvalidDataError,
            incidentFromJSON, {"xyzzy": "foo"}, number=1, validate=False,
        )


    def incidentWithJSONStuff(attributes):
        """
        Make a new incident object with incident number C{1}, and the specified
        additional attributes.  The incident is not validated.
        """
        json = dict(number=1)
        json.update(attributes)
        incidentFromJSON(json, number=1, validate=False)


    def test_incidentFromJSONEmpty(self):
        """
        Deserializing from empty JSON data produces an almost-empty incident;
        only the incident number is inserted.
        """
        incident = incidentFromJSON({}, number=1, validate=False)
        self.assertEquals(incident, Incident(number=1))


    def test_incidentFromJSONNumber(self):
        """
        Deserialize an incident number from JSON data.
        """
        incident = incidentFromJSON(
            {JSON.incident_number.value: 1}, number=1, validate=False
        )
        self.assertEquals(incident.number, 1)


    def test_incidentFromJSONNumberMissing(self):
        """
        Deserializing without an incident number from JSON data uses the number
        passed in as an argument.
        """
        incident = incidentFromJSON({}, number=1, validate=False)
        self.assertEquals(incident.number, 1)


    def test_incidentFromJSONNumberWrong(self):
        """
        Deserializing a incident number from JSON data while providing a
        different incident number as an argument raises L{InvalidDataError}.
        """
        self.assertRaises(
            InvalidDataError,
            incidentFromJSON, {JSON.incident_number.value: 1}, number=2
        )


    def test_incidentFromJSONPriority(self):
        """
        Deserialize an incident priority from JSON data.
        """
        incident = incidentFromJSON(
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
        incident = incidentFromJSON(
            {
                JSON.incident_number.value: 1,
                JSON.incident_summary.value: "A B C",
            },
            number=1, validate=False
        )
        self.assertEquals(incident.summary, "A B C")


    def test_incidentFromJSONTextOnlyLocation(self):
        """
        Deserialize a text only location from JSON data.
        """
        incident = incidentFromJSON(
            {
                JSON.incident_number.value: 1,
                JSON.incident_location.value: {
                    JSON.location_type.value: JSON.location_type_text.value,
                    JSON.location_name.value: "Ranger Outpost Zero",
                    JSON.location_garett_description.value: (
                        "Halfway between the Man and the Temple"
                    ),
                },
            },
            number=1, validate=False
        )
        self.assertEquals(
            incident.location,
            Location(
                name="Ranger Outpost Zero",
                address=TextOnlyAddress(
                    description="Halfway between the Man and the Temple",
                ),
            )
        )


    def test_incidentFromJSONTextOnlyLocationNoneDescription(self):
        """
        Deserialize a text only location from JSON data with C{None}
        description.
        """
        incident = incidentFromJSON(
            {
                JSON.incident_number.value: 1,
                JSON.incident_location.value: {
                    JSON.location_type.value: JSON.location_type_text.value,
                    JSON.location_name.value: "Ranger Outpost Zero",
                    JSON.location_garett_description.value: None,
                },
            },
            number=1, validate=False
        )
        self.assertEquals(
            incident.location,
            Location(name="Ranger Outpost Zero", address=None)
        )


    def test_incidentFromJSONGarettLocation(self):
        """
        Deserialize a Rod Garett location from JSON data.
        """
        incident = incidentFromJSON(
            {
                JSON.incident_number.value: 1,
                JSON.incident_location.value: {
                    JSON.location_type.value: JSON.location_type_garett.value,
                    JSON.location_name.value: "Tokyo",
                    JSON.location_garett_concentric.value: 3,  # 3 == C
                    JSON.location_garett_radial_hour.value: 9,
                    JSON.location_garett_radial_minute.value: 0,
                    JSON.location_garett_description.value: "Opposite ESD",
                },
            },
            number=1, validate=False
        )
        self.assertEquals(
            incident.location,
            Location(
                name="Tokyo",
                address=RodGarettAddress(
                    concentric=3, radialHour=9, radialMinute=0,
                    description="Opposite ESD",
                ),
            )
        )


    def test_incidentFromJSONGarettLocationNoneValues(self):
        """
        Deserialize a Rod Garett location from JSON data with C{None} values.
        """
        incident = incidentFromJSON(
            {
                JSON.incident_number.value: 1,
                JSON.incident_location.value: {
                    JSON.location_type.value: JSON.location_type_garett.value,
                    JSON.location_name.value: "Tokyo",
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
            Location(name="Tokyo", address=None)
        )


    def test_incidentFromJSONLegacyLocation(self):
        """
        Deserialize a location from pre-2015 JSON data.
        """
        incident = incidentFromJSON(
            {
                JSON.incident_number.value: 1,
                JSON._location_name.value: "Tokyo",
                JSON._location_address.value: "9:00 & C",
            },
            number=1, validate=False
        )
        self.assertEquals(
            incident.location,
            Location(name="Tokyo", address=TextOnlyAddress("9:00 & C"))
        )


    def test_incidentFromJSONLegacyLocationNoneValues(self):
        """
        Deserialize a location from pre-2015 JSON data with C{None} name and/or
        address.
        """
        incident = incidentFromJSON(
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
        incident = incidentFromJSON(
            {JSON.incident_number.value: 1},
            number=1, validate=False
        )
        self.assertEquals(incident.location, None)


    def test_incidentFromJSONRangers(self):
        """
        Deserialize Rangers from JSON data.
        """
        incident = incidentFromJSON(
            {
                JSON.incident_number.value: 1,
                JSON.ranger_handles.value: ["Tool", "Tulsa"],
            },
            number=1, validate=False
        )
        self.assertEquals(
            incident.rangers,
            frozenset((
                Ranger("Tool", None, None),
                Ranger("Tulsa", None, None),
            ))
        )


    def test_incidentFromJSONRangersMissing(self):
        """
        Deserialize an incident with no Rangers from JSON data.
        """
        incident = incidentFromJSON(
            {JSON.incident_number.value: 1},
            number=1, validate=False
        )
        self.assertEquals(incident.rangers, None)


    def test_incidentFromJSONRangersEmpty(self):
        """
        Deserialize an incident with empty Rangers from JSON data.
        """
        incident = incidentFromJSON(
            {
                JSON.incident_number.value: 1,
                JSON.ranger_handles.value: [],
            },
            number=1, validate=False
        )
        self.assertEquals(incident.rangers, frozenset())


    def test_incidentFromJSONTypes(self):
        """
        Deserialize incident types from JSON data.
        """
        incident = incidentFromJSON(
            {
                JSON.incident_number.value: 1,
                JSON.incident_types.value: ["Footsie", "Jacks"],
            },
            number=1, validate=False
        )
        self.assertEquals(
            incident.incidentTypes, frozenset(("Footsie", "Jacks"))
        )


    def test_incidentFromJSONTypesMissing(self):
        """
        Deserialize an incident with no incident types from JSON data.
        """
        incident = incidentFromJSON(
            {JSON.incident_number.value: 1},
            number=1, validate=False
        )
        self.assertEquals(incident.incidentTypes, None)


    def test_incidentFromJSONTypesEmpty(self):
        """
        Deserialize an incident with empty incident types from JSON data.
        """
        incident = incidentFromJSON(
            {
                JSON.incident_number.value: 1,
                JSON.incident_types.value: [],
            },
            number=1, validate=False
        )
        self.assertEquals(
            incident.incidentTypes, frozenset()
        )


    def test_incidentFromJSONEntries(self):
        """
        Deserialize report entries from JSON data.
        """
        incident = incidentFromJSON(
            {
                JSON.incident_number.value: 1,
                JSON.report_entries.value: [
                    {
                        JSON.entry_author.value: "Tool",
                        JSON.entry_text.value: "1 2 3",
                        JSON.entry_created.value: dateTimeAsRFC3339Text(time1),
                    },
                    {
                        JSON.entry_author.value: "Tulsa",
                        JSON.entry_text.value: "A B C",
                        JSON.entry_created.value: dateTimeAsRFC3339Text(time2),
                    },
                ],
            },
            number=1, validate=False
        )
        self.assertEquals(
            incident.reportEntries,
            (
                ReportEntry(author="Tool", text="1 2 3", created=time1),
                ReportEntry(author="Tulsa", text="A B C", created=time2),
            )
        )


    def test_incidentFromJSONEntriesMissing(self):
        """
        Deserialize an incident with no report entries from JSON data.
        """
        incident = incidentFromJSON(
            {JSON.incident_number.value: 1},
            number=1, validate=False
        )
        self.assertEquals(incident.reportEntries, None)


    def test_incidentFromJSONEntriesEmpty(self):
        """
        Deserialize an incident with empty report entries from JSON data.
        """
        incident = incidentFromJSON(
            {
                JSON.incident_number.value: 1,
                JSON.report_entries.value: [],
            },
            number=1, validate=False
        )
        self.assertEquals(incident.reportEntries, ())


    def test_incidentFromJSONCreated(self):
        """
        Deserialize an incident created time from JSON data.
        """
        incident = incidentFromJSON(
            {
                JSON.incident_number.value: 1,
                JSON.incident_created.value: dateTimeAsRFC3339Text(time1),
            },
            number=1, validate=False
        )
        self.assertEquals(incident.created, time1)


    def test_incidentFromJSONCreatedMissing(self):
        """
        Deserialize with no incident created time from JSON data.
        """
        incident = incidentFromJSON(
            {JSON.incident_number.value: 1},
            number=1, validate=False
        )
        self.assertEquals(incident.created, None)


    def test_incidentFromJSONState(self):
        """
        Deserialize an incident created state from JSON data.
        """
        incident = incidentFromJSON(
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
        incident = incidentFromJSON(
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
            incident = incidentFromJSON(
                {
                    JSON.incident_number.value: 1,
                    json_key: "2012-09-01T21:00:00Z",
                },
                number=1, validate=False
            )
            self.assertEquals(incident.state, state)



class IncidentSerializationTests(unittest.TestCase):
    """
    Tests for L{incidentAsJSON}.
    """

    def test_incidentAsJSONNumber(self):
        """
        Serialize with incident number.
        """
        self.assertEquals(
            {JSON.incident_number.value: 1},
            incidentAsJSON(Incident(number=1))
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
            incidentAsJSON(Incident(number=1, priority=2))
        )


    def test_incidentAsJSONSummary(self):
        """
        Serialize with summary.
        """
        self.assertEquals(
            {
                JSON.incident_number.value: 1,
                JSON.incident_summary.value: "A B C",
            },
            incidentAsJSON(Incident(number=1, summary="A B C"))
        )


    def test_incidentAsJSONLocationWithNoneAddress(self):
        """
        Serialize with a location with a C{None} address.
        """
        self.assertEquals(
            {
                JSON.incident_number.value: 1,
                JSON.incident_location.value: {
                    JSON.location_name.value: "Tokyo",
                    JSON.location_type.value: JSON.location_type_text.value,
                    JSON.location_text_description.value: None,
                },
            },
            incidentAsJSON(
                Incident(
                    number=1,
                    location=Location(name="Tokyo", address=None),
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
            incidentAsJSON(
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
                    JSON.location_name.value: "Ranger Outpost Zero",
                    JSON.location_type.value: JSON.location_type_text.value,
                    JSON.location_text_description.value: (
                        "Halfway between the Man and the Temple"
                    ),
                },
            },
            incidentAsJSON(
                Incident(
                    number=1,
                    location=Location(
                        name="Ranger Outpost Zero",
                        address=TextOnlyAddress(
                            description=(
                                "Halfway between the Man and the Temple"
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
                    JSON.location_name.value: "Ranger Outpost Zero",
                    JSON.location_type.value: JSON.location_type_text.value,
                    JSON.location_text_description.value: None,
                },
            },
            incidentAsJSON(
                Incident(
                    number=1,
                    location=Location(
                        name="Ranger Outpost Zero",
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
                    JSON.location_name.value: "Tokyo",
                    JSON.location_type.value: JSON.location_type_garett.value,
                    JSON.location_garett_concentric.value: 3,  # 3 == C
                    JSON.location_garett_radial_hour.value: 9,
                    JSON.location_garett_radial_minute.value: 0,
                    JSON.location_garett_description.value: (
                        "Back of 9:00 plaza, opposite Medical"
                    ),
                }
            },
            incidentAsJSON(
                Incident(
                    number=1,
                    location=Location(
                        name="Tokyo",
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
                    JSON.location_name.value: "Tokyo",
                    JSON.location_type.value: JSON.location_type_garett.value,
                    JSON.location_garett_concentric.value: None,
                    JSON.location_garett_radial_hour.value: None,
                    JSON.location_garett_radial_minute.value: None,
                    JSON.location_garett_description.value: None,
                }
            },
            incidentAsJSON(
                Incident(
                    number=1,
                    location=Location(
                        name="Tokyo",
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
        result = incidentAsJSON(
            Incident(
                number=1,
                rangers=(
                    Ranger("Tool", None, None),
                    Ranger("Tulsa", None, None),
                ),
            )
        )

        self.assertEquals(
            frozenset(result.keys()),
            frozenset((JSON.incident_number.value, JSON.ranger_handles.value))
        )
        self.assertEquals(result[JSON.incident_number.value], 1)
        self.assertEquals(
            frozenset(result[JSON.ranger_handles.value]),
            frozenset(("Tool", "Tulsa"))
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
            incidentAsJSON(Incident(number=1, rangers=()))
        )


    def test_incidentAsJSONTypes(self):
        """
        Serialize with some incident types.
        """
        result = incidentAsJSON(
            Incident(
                number=1,
                incidentTypes=("Footsie", "Jacks"),
            )
        )

        self.assertEquals(
            frozenset(result.keys()),
            frozenset((JSON.incident_number.value, JSON.incident_types.value))
        )
        self.assertEquals(result[JSON.incident_number.value], 1)
        self.assertEquals(
            frozenset(result[JSON.incident_types.value]),
            frozenset(("Footsie", "Jacks"))
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
            incidentAsJSON(Incident(number=1, incidentTypes=()))
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
                        JSON.entry_author.value: "Tool",
                        JSON.entry_text.value: "1 2 3",
                        JSON.entry_created.value: dateTimeAsRFC3339Text(time1),
                        JSON.entry_system.value: False,
                    },
                    {
                        JSON.entry_author.value: "Tulsa",
                        JSON.entry_text.value: "A B C",
                        JSON.entry_created.value: dateTimeAsRFC3339Text(time2),
                        JSON.entry_system.value: False,
                    },
                ],
            },
            incidentAsJSON(
                Incident(
                    number=1,
                    reportEntries=(
                        ReportEntry(
                            author="Tool", text="1 2 3", created=time1
                        ),
                        ReportEntry(
                            author="Tulsa", text="A B C", created=time2
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
            incidentAsJSON(
                Incident(number=1, reportEntries=())
            )
        )


    def test_incidentAsJSONCreated(self):
        """
        Serialize with created.
        """
        self.assertEquals(
            {
                JSON.incident_number.value: 1,
                JSON.incident_created.value: dateTimeAsRFC3339Text(time1),
            },
            incidentAsJSON(
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
            incidentAsJSON(
                Incident(
                    number=1,
                    state=IncidentState.on_scene,
                )
            )
        )



class RangerSerializationTests(unittest.TestCase):
    """
    Tests for L{rangerAsJSON}.
    """

    def test_rangerAsJSONHandle(self):
        """
        Serialize with handle.
        """
        self.assertEquals(
            {
                JSON.ranger_handle.value: "Tool",
                JSON.ranger_name.value: None,
                JSON.ranger_status.value: None,
                JSON.ranger_dms_id.value: None,
                JSON.ranger_email.value: None,
                JSON.ranger_on_site.value: None,
            },
            rangerAsJSON(Ranger(handle="Tool", name=None, status=None))
        )


    def test_rangerAsJSONHandleNameStatus(self):
        """
        Serialize with handle, name, status.
        """
        self.assertEquals(
            {
                JSON.ranger_handle.value: "Tool",
                JSON.ranger_name.value: "Wilfredo S\xe1nchez",
                JSON.ranger_status.value: "vintage",
                JSON.ranger_dms_id.value: 1234,
                JSON.ranger_email.value: "tool@burningman.org",
                JSON.ranger_on_site.value: False,
            },
            rangerAsJSON(Ranger(
                handle="Tool", name="Wilfredo S\xe1nchez", status="vintage",
                dmsID=1234, email="tool@burningman.org", onSite=False,
            ))
        )



class LocationSerializationTests(unittest.TestCase):
    """
    Tests for L{locationAsJSON}.
    """

    def test_locationAsJSONName(self):
        """
        Serialize with name.
        """
        self.assertEquals(
            {
                "type": "text",
                "name": "Ranger Outpost Tokyo",
                "description": None,
            },
            locationAsJSON(Location(name="Ranger Outpost Tokyo"))
        )

    def test_locationAsJSONTextOnlyAddress(self):
        """
        Serialize with address.
        """
        self.assertEquals(
            {
                "type": "text",
                "name": None,
                "description": "The Temple",
            },
            locationAsJSON(Location(address=TextOnlyAddress("The Temple")))
        )

    # FIXME: more complete testing of locationAsJSON() is in serialization
    # tests above; move that testing here.
