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
Tests for L{ims.directory.file._directory}.
"""

from pathlib import Path
from random import Random
from typing import Any, Dict, FrozenSet, List, Mapping, Sequence, Tuple, Union
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis.strategies import lists, randoms, text

from ims.ext.trial import TestCase
from ims.model import Position, Ranger, RangerStatus
from ims.model.strategies import positions, rangers

from .._directory import (
    FileDirectory,
    positionFromMapping,
    positionsFromMappings,
    rangerFromMapping,
    rangersFromMappings,
    statusFromID,
)
from ..._directory import DirectoryError, RangerUser


__all__ = ()


rangerBeepBoop = Ranger(
    handle="Beep Boop",
    name="Ann Droid",
    status=RangerStatus.active,
    email=("ad@example.com",),
    enabled=True,
    directoryID=None,
    password="73415783-F274-4505-9F3B-42F07E219A56",
)
rangerSlumber = Ranger(
    handle="Slumber",
    name="Sleepy T. Dwarf",
    status=RangerStatus.inactive,
    email=("slumber@example.com", "sleepy@example.com"),
    enabled=True,
    directoryID=None,
    password="5A23692C-B751-4567-8848-F4F177C9EF69",
)
rangerYouRine = Ranger(
    handle="YouRine",
    name="I. P. Freely",
    status=RangerStatus.active,
    email=("yourine@example.com",),
    enabled=False,
    directoryID=None,
    password="43272914-C2DB-460A-B1AB-E3A4743DC5B9",
)
rangerNine = Ranger(
    handle="Nine",
    name="Nein Statushaven",
    status=RangerStatus.other,
    email=(),
    enabled=True,
    directoryID=None,
    password=None,
)

testRangers = frozenset(
    (rangerBeepBoop, rangerSlumber, rangerYouRine, rangerNine)
)

testPositions: FrozenSet[Tuple[str, Sequence[str]]] = frozenset(
    (
        ("Build Team", ("Beep Boop", "Slumber")),
        ("Shift Leads", ("Slumber", "YouRine")),
    )
)


def rangerAsDict(ranger: Ranger, random: Random) -> Dict[str, Any]:
    email: Union[str, List[str]] = list(ranger.email)
    if len(ranger.email) == 1:
        # We allow either a string or a list in the YAML when you have a single
        # email address, so this creates both.
        email = random.choice((email[0], email))

    return dict(
        handle=ranger.handle,
        name=ranger.name,
        status=ranger.status.name,
        email=email,
        enabled=ranger.enabled,
        # directoryID is not used
        password=ranger.password,
    )


def positionAsDict(position: Position) -> Dict[str, Any]:
    return dict(name=position.name, members=list(position.members))


class UtilityTests(TestCase):
    """
    Tests for utilities.
    """

    def test_statusFromID_known(self) -> None:
        for name, status in (
            ("active", RangerStatus.active),
            ("inactive", RangerStatus.inactive),
            ("vintage", RangerStatus.vintage),
        ):
            self.assertIdentical(statusFromID(name), status)

    @given(
        text().filter(
            lambda name: name not in ("active", "inactive", "vintage")
        )
    )
    @settings(max_examples=10)
    def test_statusFromID_unknown(self, name: str) -> None:
        self.assertIdentical(statusFromID(name), RangerStatus.other)

    @given(lists(rangers()), randoms())
    @settings(max_examples=10)
    def test_rangersFromMappings(
        self, rangers: Sequence[Ranger], random: Random
    ) -> None:
        rangers = [ranger.replace(directoryID=None) for ranger in rangers]
        rangerDicts = [rangerAsDict(ranger, random) for ranger in rangers]
        result = list(rangersFromMappings(rangerDicts))

        self.assertEqual(result, rangers)

    def test_rangersFromMappings_notList(self) -> None:
        e = self.assertRaises(DirectoryError, list, rangersFromMappings(()))
        self.assertEqual(str(e), "Rangers must be sequence: ()")

    def test_rangersFromMappings_reraise(self) -> None:
        e = self.assertRaises(
            DirectoryError,
            list,
            rangersFromMappings([None]),  # type: ignore[list-item]
        )
        self.assertEqual(str(e), "Ranger must be mapping: None")

    def test_rangersFromMappings_error(self) -> None:
        def poof(mapping: Mapping[str, Any]) -> Ranger:
            raise RuntimeError("poof")

        with patch("ims.directory.file._directory.rangerFromMapping", poof):
            e = self.assertRaises(
                DirectoryError, list, rangersFromMappings([{}])
            )
            self.assertEqual(str(e), "Unable to parse Ranger records: poof")

    @given(rangers(), randoms())
    def test_rangerFromMapping(self, ranger: Ranger, random: Random) -> None:
        ranger = ranger.replace(directoryID=None)
        rangerDict = rangerAsDict(ranger, random)
        result = rangerFromMapping(rangerDict)

        self.assertEqual(result, ranger)

    def test_rangerFromMapping_notDict(self) -> None:
        e = self.assertRaises(DirectoryError, rangerFromMapping, ())
        self.assertEqual(str(e), "Ranger must be mapping: ()")

    @given(rangers(), randoms())
    @settings(max_examples=10)
    def test_rangerFromMapping_noHandle(
        self, ranger: Ranger, random: Random
    ) -> None:
        ranger = ranger.replace(directoryID=None)
        rangerDict = rangerAsDict(ranger, random)
        del rangerDict["handle"]

        e = self.assertRaises(DirectoryError, rangerFromMapping, rangerDict)
        self.assertEqual(str(e), f"Ranger must have handle: {rangerDict!r}")

    @given(rangers(), randoms())
    @settings(max_examples=10)
    def test_rangerFromMapping_handleNotText(
        self, ranger: Ranger, random: Random
    ) -> None:
        ranger = ranger.replace(directoryID=None)
        rangerDict = rangerAsDict(ranger, random)
        handle = rangerDict["handle"].encode("utf-8")
        rangerDict["handle"] = handle

        e = self.assertRaises(DirectoryError, rangerFromMapping, rangerDict)
        self.assertEqual(str(e), f"Ranger handle must be text: {handle!r}")

    @given(rangers(), randoms())
    @settings(max_examples=10)
    def test_rangerFromMapping_nameNotText(
        self, ranger: Ranger, random: Random
    ) -> None:
        ranger = ranger.replace(directoryID=None)
        rangerDict = rangerAsDict(ranger, random)
        name = rangerDict["name"].encode("utf-8")
        rangerDict["name"] = name

        e = self.assertRaises(DirectoryError, rangerFromMapping, rangerDict)
        self.assertEqual(str(e), f"Ranger name must be text: {name!r}")

    @given(rangers(), randoms())
    @settings(max_examples=10)
    def test_rangerFromMapping_statusNotText(
        self, ranger: Ranger, random: Random
    ) -> None:
        ranger = ranger.replace(directoryID=None)
        rangerDict = rangerAsDict(ranger, random)
        status = rangerDict["status"].encode("utf-8")
        rangerDict["status"] = status

        e = self.assertRaises(DirectoryError, rangerFromMapping, rangerDict)
        self.assertEqual(str(e), f"Ranger status must be text: {status!r}")

    @given(
        rangers().filter(lambda r: len(r.email) > 0), randoms(),
    )
    @settings(max_examples=10)
    def test_rangerFromMapping_emailNotText(
        self, ranger: Ranger, random: Random
    ) -> None:
        ranger = ranger.replace(directoryID=None)

        rangerDict = rangerAsDict(ranger, random)

        # Make sure we have email in list form for this test.
        if type(rangerDict["email"]) is str:
            rangerDict["email"] = [rangerDict["email"]]

        index = random.choice(range(len(ranger.email)))
        email = rangerDict["email"][index].encode("utf-8")
        rangerDict["email"][index] = email

        e = self.assertRaises(DirectoryError, rangerFromMapping, rangerDict)
        self.assertEqual(str(e), f"Ranger email must be text: {email!r}")

    @given(rangers(), randoms())
    @settings(max_examples=10)
    def test_rangerFromMapping_emailNotTextOrSequenceOfText(
        self, ranger: Ranger, random: Random
    ) -> None:
        ranger = ranger.replace(directoryID=None)
        rangerDict = rangerAsDict(ranger, random)
        email = tuple(rangerDict["email"])
        rangerDict["email"] = email

        e = self.assertRaises(DirectoryError, rangerFromMapping, rangerDict)
        self.assertEqual(
            str(e), f"Ranger email must be text or sequence of text: {email!r}"
        )

    @given(rangers(), randoms())
    @settings(max_examples=10)
    def test_rangerFromMapping_enabledNotBool(
        self, ranger: Ranger, random: Random
    ) -> None:
        ranger = ranger.replace(directoryID=None)
        rangerDict = rangerAsDict(ranger, random)
        rangerDict["enabled"] = None

        e = self.assertRaises(DirectoryError, rangerFromMapping, rangerDict)
        self.assertEqual(str(e), "Ranger enabled must be boolean: None")

    @given(rangers(), randoms())
    @settings(max_examples=10)
    def test_rangerFromMapping_passwordNotText(
        self, ranger: Ranger, random: Random
    ) -> None:
        ranger = ranger.replace(directoryID=None)
        rangerDict = rangerAsDict(ranger, random)
        rangerDict["password"] = 0

        e = self.assertRaises(DirectoryError, rangerFromMapping, rangerDict)
        self.assertEqual(str(e), "Ranger password must be text: 0")

    @given(lists(positions()))
    @settings(max_examples=10)
    def test_positionsFromMappings(self, positions: Sequence[Position]) -> None:
        positionDicts = [positionAsDict(position) for position in positions]
        result = list(positionsFromMappings(positionDicts))

        self.assertEqual(result, positions)

    def test_positionsFromMappings_notList(self) -> None:
        e = self.assertRaises(DirectoryError, list, positionsFromMappings(()))
        self.assertEqual(str(e), "Positions must be sequence: ()")

    def test_positionsFromMappings_reraise(self) -> None:
        e = self.assertRaises(
            DirectoryError,
            list,
            positionsFromMappings([None]),  # type: ignore[list-item]
        )
        self.assertEqual(str(e), "Position must be mapping: None")

    def test_positionsFromMappings_error(self) -> None:
        def poof(mapping: Mapping[str, Any]) -> Position:
            raise RuntimeError("poof")

        with patch("ims.directory.file._directory.positionFromMapping", poof):
            e = self.assertRaises(
                DirectoryError, list, positionsFromMappings([{}])
            )
            self.assertEqual(str(e), "Unable to parse position records: poof")

    @given(positions())
    @settings(max_examples=10)
    def test_positionFromMapping_noName(self, position: Position) -> None:
        positionDict = positionAsDict(position)
        del positionDict["name"]

        e = self.assertRaises(DirectoryError, positionFromMapping, positionDict)
        self.assertEqual(str(e), f"Position must have name: {positionDict!r}")

    @given(positions())
    @settings(max_examples=10)
    def test_positionFromMapping_nameNotText(self, position: Position) -> None:
        positionDict = positionAsDict(position)
        name = positionDict["name"].encode("utf-8")
        positionDict["name"] = name

        e = self.assertRaises(DirectoryError, positionFromMapping, positionDict)
        self.assertEqual(str(e), f"Position name must be text: {name!r}")

    @given(positions().filter(lambda p: len(p.members) > 0), randoms())
    @settings(max_examples=10)
    def test_positionFromMapping_membersNotText(
        self, position: Position, random: Random
    ) -> None:
        positionDict = positionAsDict(position)

        index = random.choice(range(len(position.members)))
        members = positionDict["members"][index].encode("utf-8")
        positionDict["members"][index] = members

        e = self.assertRaises(DirectoryError, positionFromMapping, positionDict)
        self.assertEqual(str(e), f"Position members must be text: {members!r}")

    @given(positions())
    @settings(max_examples=10)
    def test_positionFromMapping_membersNotSequenceOfText(
        self, position: Position
    ) -> None:
        positionDict = positionAsDict(position)
        members = tuple(positionDict["members"])
        positionDict["members"] = members

        e = self.assertRaises(DirectoryError, positionFromMapping, positionDict)
        self.assertEqual(
            str(e), f"Position members must be sequence of text: {members!r}"
        )


class FileDirectoryTests(TestCase):
    """
    Tests for :class:`FileDirectory`
    """

    def directory(self) -> FileDirectory:
        path = Path(__file__).parent / "directory.yaml"
        return FileDirectory(path=path)

    def test_personnel(self) -> None:
        directory = self.directory()
        personnel = set(self.successResultOf(directory.personnel()))

        self.assertEqual(personnel, testRangers)

    def assertCorrectPositions(self, user: RangerUser) -> None:
        for name, members in testPositions:
            if user.ranger.handle in members:
                self.assertIn(name, user.groups)

    def test_lookupUser_handle(self) -> None:
        directory = self.directory()

        for ranger in testRangers:
            user = self.successResultOf(directory.lookupUser(ranger.handle))
            self.assertEqual(user.ranger, ranger)
            self.assertCorrectPositions(user)

    def test_lookupUser_email(self) -> None:
        directory = self.directory()

        for ranger in testRangers:
            for email in ranger.email:
                user = self.successResultOf(directory.lookupUser(email))
                self.assertEqual(user.ranger, ranger)
                self.assertCorrectPositions(user)
