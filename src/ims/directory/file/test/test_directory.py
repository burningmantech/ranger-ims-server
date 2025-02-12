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

from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractContextManager
from pathlib import Path
from random import Random
from time import time
from typing import Any, TextIO
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis.strategies import lists, randoms, text

from ims.ext.trial import TestCase
from ims.model import Position, Ranger, RangerStatus
from ims.model.strategies import positions, rangers

from ..._directory import DirectoryError, IMSUser
from .._directory import (
    FileDirectory,
    positionFromMapping,
    positionsFromMappings,
    rangerFromMapping,
    rangersFromMappings,
    statusFromID,
)


__all__ = ()


rangerBeepBoop = Ranger(
    handle="Beep Boop",
    status=RangerStatus.active,
    email=("ad@example.com",),
    onsite=True,
    directoryID=None,
    password="73415783-F274-4505-9F3B-42F07E219A56",  # noqa: S106
)
rangerSlumber = Ranger(
    handle="Slumber",
    status=RangerStatus.inactive,
    email=("slumber@example.com", "sleepy@example.com"),
    onsite=True,
    directoryID=None,
    password="5A23692C-B751-4567-8848-F4F177C9EF69",  # noqa: S106
)
rangerYouRine = Ranger(
    handle="YouRine",
    status=RangerStatus.active,
    email=("yourine@example.com",),
    onsite=False,
    directoryID=None,
    password="43272914-C2DB-460A-B1AB-E3A4743DC5B9",  # noqa: S106
)
rangerNine = Ranger(
    handle="Nine",
    status=RangerStatus.other,
    email=(),
    onsite=True,
    directoryID=None,
    password=None,
)

testRangers = frozenset((rangerBeepBoop, rangerSlumber, rangerYouRine, rangerNine))

testPositions: frozenset[tuple[str, Sequence[str]]] = frozenset(
    (
        ("Build Team", ("Beep Boop", "Slumber")),
        ("Shift Leads", ("Slumber", "YouRine")),
    )
)


def rangerAsDict(ranger: Ranger, random: Random) -> dict[str, Any]:
    email: str | list[str] = list(ranger.email)
    if len(ranger.email) == 1:
        # We allow either a string or a list in the YAML when you have a single
        # email address, so this creates both.
        email = random.choice((email[0], email))

    return {
        "handle": ranger.handle,
        "status": ranger.status.name,
        "email": email,
        "onsite": ranger.onsite,
        # directoryID is not used
        "password": ranger.password,
    }


def positionAsDict(position: Position) -> dict[str, Any]:
    return {"name": position.name, "members": list(position.members)}


class UtilityTests(TestCase):
    """
    Tests for utilities.
    """

    def test_statusFromID_known(self) -> None:
        for name, status in (
            ("active", RangerStatus.active),
            ("inactive", RangerStatus.inactive),
        ):
            self.assertIdentical(statusFromID(name), status)

    @given(text().filter(lambda name: name not in ("active", "inactive")))
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
        def poof(mapping: Mapping[str, Any]) -> Ranger:  # noqa: ARG001
            raise RuntimeError("poof")

        with patch("ims.directory.file._directory.rangerFromMapping", poof):
            e = self.assertRaises(DirectoryError, list, rangersFromMappings([{}]))
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
    def test_rangerFromMapping_noHandle(self, ranger: Ranger, random: Random) -> None:
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
        rangers().filter(lambda r: len(r.email) > 0),
        randoms(),
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
    def test_rangerFromMapping_onsiteNotBool(
        self, ranger: Ranger, random: Random
    ) -> None:
        ranger = ranger.replace(directoryID=None)
        rangerDict = rangerAsDict(ranger, random)
        rangerDict["onsite"] = None

        e = self.assertRaises(DirectoryError, rangerFromMapping, rangerDict)
        self.assertEqual(str(e), "Ranger onsite must be boolean: None")

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
        def poof(mapping: Mapping[str, Any]) -> Position:  # noqa: ARG001
            raise RuntimeError("poof")

        with patch("ims.directory.file._directory.positionFromMapping", poof):
            e = self.assertRaises(DirectoryError, list, positionsFromMappings([{}]))
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

    def patchTime(self) -> AbstractContextManager[Callable[[], float]]:
        self.now = time()
        self.timeIncrement = 0.1

        def fakeTime() -> float:
            self.now += self.timeIncrement
            return self.now

        return patch("ims.directory.file._directory.time", fakeTime)

    def patchDirectoryOpen(
        self,
    ) -> AbstractContextManager[Callable[[FileDirectory], TextIO]]:
        self.openCount = 0

        superOpen = FileDirectory._open

        def openAndCount(directorySelf: FileDirectory) -> TextIO:
            self.openCount += 1
            return superOpen(directorySelf)

        return patch("ims.directory.file._directory.FileDirectory._open", openAndCount)

    def patchDirectoryMTime(
        self,
    ) -> AbstractContextManager[Callable[[FileDirectory], float]]:
        self.mtime: float | None = None

        superMTime = FileDirectory._mtime

        def overridableMTime(directorySelf: FileDirectory) -> float:
            if self.mtime is None:
                return superMTime(directorySelf)
            return self.mtime

        return patch(
            "ims.directory.file._directory.FileDirectory._mtime",
            overridableMTime,
        )

    def test_reload_before(self) -> None:
        """
        Reload before the check interval only opens the file once.
        """
        directory = self.directory()

        with self.patchTime(), self.patchDirectoryOpen():
            for _count in range(4):
                directory._reload()
                directory._reload()
                directory._reload()
                directory._reload()

        self.assertEqual(self.openCount, 1)

    def test_reload_past(self) -> None:
        """
        Reload past the check interval re-opens the file.
        """
        directory = self.directory()

        with (
            self.patchTime(),
            self.patchDirectoryOpen(),
            self.patchDirectoryMTime(),
        ):
            self.timeIncrement = directory.checkInterval + 0.1
            for count in range(4):  # noqa: B007
                self.mtime = self.now
                directory._reload()

        self.assertEqual(self.openCount, count + 1)

    def test_personnel(self) -> None:
        directory = self.directory()
        personnel = set(self.successResultOf(directory.personnel()))

        self.assertEqual(personnel, testRangers)

    def assertCorrectPositions(self, user: IMSUser) -> None:
        for name, members in testPositions:
            if user.shortNames[0] in members:
                self.assertIn(name, user.groups)

    def test_lookupUser_handle(self) -> None:
        directory = self.directory()

        for ranger in testRangers:
            user = self.successResultOf(directory.lookupUser(ranger.handle))
            self.assertCorrectPositions(user)

    def test_lookupUser_email(self) -> None:
        directory = self.directory()

        for ranger in testRangers:
            for email in ranger.email:
                user = self.successResultOf(directory.lookupUser(email))
                self.assertCorrectPositions(user)
