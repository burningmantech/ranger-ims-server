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

from __future__ import print_function

import sys
from csv import reader as CSVReader

from ims.data import Location, RodGarettAddress
from ims.json import locationAsJSON, textFromJSON



concentricStreetToNumberMap = {
    u"Esplanade"        : 0,
    u"A"                : 1,
    u"B"                : 2,
    u"C"                : 3,
    u"D"                : 4,
    u"E"                : 5,
    u"F"                : 6,
    u"G"                : 7,
    u"H"                : 8,
    u"I"                : 9,
    u"J"                : 10,
    u"K"                : 11,
    u"L"                : 12,
    u"3:00 Plaza"       : 300,
    u"3:00 Public Plaza": 305,
    u"4:30 Plaza"       : 430,
    u"Center Camp Plaza": 600,
    u"Rte 66"           : 601,
    u"Rod's Road"       : 602,
    u"6:00 Public Plaza": 605,
    u"7:30 Plaza"       : 730,
    u"9:00 Plaza"       : 900,
    u"9:00 Public Plaza": 905,
}


def parseLocations(inStream):
    reader = CSVReader(inStream)

    for (
        category,
        campName,
        textAddress,
        frontageAddress,
        crossStreet,
        dimensions
    ) in reader:
        if category == b"Category" and campName == b"Camp Name":
            # Header row
            continue

        yield parseLocation(
            category=category,
            campName=campName,
            textAddress=textAddress,
            frontageAddress=frontageAddress,
            crossStreet=crossStreet,
            dimensions=dimensions,
        )


def parseLocation(
    category,
    campName,
    textAddress,
    frontageAddress,
    crossStreet,
    dimensions,
):
    encoding = "macroman"

    category        = category.decode(encoding)
    campName        = campName.decode(encoding)
    textAddress     = textAddress.decode(encoding)
    frontageAddress = frontageAddress.decode(encoding)
    crossStreet     = crossStreet.decode(encoding)
    dimensions      = dimensions.decode(encoding)

    # print(campName)
    concentric   = None
    radialHour   = None
    radialMinute = None
    plaza        = None

    for streetAddress in (frontageAddress, crossStreet):
        if not streetAddress:
            continue
        try:
            radialHour, radialMinute, plaza = parseRadialStreetAddress(
                streetAddress
            )
        except RadialStreetAddressParseError:
            try:
                concentric = parseConcentricStreetAddress(streetAddress)
            except ConcentricStreetAddressParseError:
                sys.stderr.write(
                    "WARNING: unable to parse street address: {!r}\n"
                    .format(streetAddress)
                )

    if category == u"Camp within a Village":
        description = textAddress
    elif category == u"Burning Man Department":
        description = u"Burning Man Department"
    else:
        description = category

    if dimensions:
        description = u"{} {}".format(
            description, dimensions.replace(u" ", u"")
        )

    if plaza:
        # print(
        #     "{}: {!r} @ {!r}\n -> {}:{}@{} - {!r}".format(
        #         campName, frontageAddress, crossStreet,
        #         radialHour, radialMinute, concentric, plaza
        #     )
        # )
        description = u"{}, {}".format(plaza, description)

    address = RodGarettAddress(
        concentric=concentric,
        radialHour=radialHour, radialMinute=radialMinute,
        description=description,
    )

    return Location(name=campName, address=address)


def parseConcentricStreetAddress(address):
    number = concentricStreetToNumberMap.get(address, None)

    if number is None:
        if address.startswith(u"Rte 66 Qrtr "):
            number = concentricStreetToNumberMap["Rte 66"]
        else:
            raise ConcentricStreetAddressParseError()

    return number


def parseRadialStreetAddress(address):
    try:
        hour, minute = address.split(":")
    except ValueError:
        raise RadialStreetAddressParseError()

    try:
        minute, plaza = minute.split(" ", 1)
    except ValueError:
        plaza = None

    if plaza in ("Plaza", "Public Plaza"):
        # Plazas are "concentric" streets, not radials
        raise RadialStreetAddressParseError()
    elif plaza:
        plaza = address

    try:
        minute = int(minute)
        hour   = int(hour)
    except ValueError:
        raise RadialStreetAddressParseError()

    return hour, minute, plaza



class StreetAddressParseError(Exception):
    pass

class ConcentricStreetAddressParseError(StreetAddressParseError):
    pass

class RadialStreetAddressParseError(StreetAddressParseError):
    pass



if __name__ == "__main__":
    with open(sys.argv[1], "rU") as inStream:
        locations = parseLocations(inStream)
        json = [locationAsJSON(location) for location in locations]

    sys.stdout.write(textFromJSON(json))
