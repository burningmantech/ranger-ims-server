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
from typing import FrozenSet, Sequence, Tuple

from ims.ext.trial import TestCase
from ims.model import Ranger, RangerStatus

from .._directory import FileDirectory
from ..._directory import RangerUser


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

testRangers = frozenset((
    rangerBeepBoop, rangerSlumber, rangerYouRine, rangerNine
))

testPositions: FrozenSet[Tuple[str, Sequence[str]]] = frozenset((
    ("Build Team", ("Beep Boop", "Slumber")),
    ("Shift Leads", ("Slumber", "YouRine")),
))


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
