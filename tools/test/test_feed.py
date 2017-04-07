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
Tests for L{tools.feed}.
"""

import twisted.trial.unittest

from ims.data import Location, RodGarettAddress

from tools.feed import parseLocation



class ParseLocationTests(twisted.trial.unittest.TestCase):
    """
    Tests for L{tools.feed.parseLocation}
    """

    def test_basic(self):
        """
        Basic camp info
        """
        streets = ("9:00", "C")
        for front, cross in (streets, reversed(streets)):
            location = parseLocation(
                "Burning Man Department",
                "Ranger Outpost Tokyo",
                "9:00 & Carny",
                front, cross,
                "260 x 160"
            )
            self.assertEquals(
                location,
                Location(
                    name="Ranger Outpost Tokyo",
                    address=RodGarettAddress(
                        concentric=3, radialHour=9, radialMinute=0,
                        description="Burning Man Department 260x160",
                    ),
                )
            )


    def test_portalBlank(self):
        """
        One street is radial & "Portal", cross street is blank.
        """
        streets = ("6:00 Portal", "")
        for front, cross in (streets, reversed(streets)):
            location = parseLocation(
                "Burning Man Department",
                "Fire Conclave Convergence",
                "6:00 Portal",
                front, cross,
                "133 x 80"
            )
            self.assertEquals(
                location,
                Location(
                    name="Fire Conclave Convergence",
                    address=RodGarettAddress(
                        concentric=None, radialHour=6, radialMinute=0,
                        description=(
                            "6:00 Portal, Burning Man Department 133x80"
                        ),
                    ),
                )
            )


    def test_portalCross(self):
        """
        One street is radial & "Portal", cross street is a concentric.
        """
        streets = ("9:00 Portal", "A")
        for front, cross in (streets, reversed(streets)):
            location = parseLocation(
                "Theme Camp",
                "Camp at Portal",
                "Portal & Arcade",
                front, cross,
                "100 x 150+"
            )
            self.assertEquals(
                location,
                Location(
                    name="Camp at Portal",
                    address=RodGarettAddress(
                        concentric=1, radialHour=9, radialMinute=0,
                        description="9:00 Portal, Theme Camp 100x150+",
                    ),
                )
            )


    def test_portalPortal(self):
        """
        Both streets are radial & "Portal".
        """
        streets = ("9:00 Portal", "9:00 Portal")
        for front, cross in (streets, reversed(streets)):
            location = parseLocation(
                "Theme Camp",
                "Camp at Portal",
                "9:00 Portal @ 9:00 Portal",
                front, cross,
                "50 x 200"
            )
            self.assertEquals(
                location,
                Location(
                    name="Camp at Portal",
                    address=RodGarettAddress(
                        concentric=None, radialHour=9, radialMinute=0,
                        description="9:00 Portal, Theme Camp 50x200",
                    ),
                )
            )


    def test_plazaRadial(self):
        """
        One street is a plaza (which is concentric), cross is radial in plaza.
        """
        streets = ("9:00 Plaza", "4:30")
        for front, cross in (streets, reversed(streets)):
            location = parseLocation(
                "Burning Man Department",
                "Ice Nine",
                "9:00 Plaza @ 4:30",
                front, cross,
                "70 x 100+"
            )
            self.assertEquals(
                location,
                Location(
                    name="Ice Nine",
                    address=RodGarettAddress(
                        concentric=900, radialHour=4, radialMinute=30,
                        description="Burning Man Department 70x100+",
                    ),
                )
            )


    def test_publicPlazaRadial(self):
        """
        One street is a public plaza (which is concentric), cross is radial in
        plaza.
        """
        streets = ("9:00 Public Plaza", "12:15")
        for front, cross in (streets, reversed(streets)):
            location = parseLocation(
                "Village",
                "Village in Public Plaza",
                "9:00 Public Plaza @ 12:15",
                front, cross,
                "110 x 200-"
            )
            self.assertEquals(
                location,
                Location(
                    name="Village in Public Plaza",
                    address=RodGarettAddress(
                        concentric=905, radialHour=12, radialMinute=15,
                        description="Village 110x200-",
                    ),
                )
            )
