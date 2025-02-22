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
Tests for L{ims.directory.clubhouse_db._directory}.
"""

from ims.directory import IMSUser
from ims.directory.clubhouse_db import DMSDirectory
from ims.directory.clubhouse_db._dms import Position, Team
from ims.ext.trial import TestCase
from ims.model import Ranger, RangerStatus


__all__ = ()


def _ranger_alpha() -> Ranger:
    return Ranger(
        handle="Alpha",
        status=RangerStatus.active,
        email=frozenset(["alpha@example.com"]),
        onsite=False,
        directoryID=None,
    )


def _ranger_beta() -> Ranger:
    return Ranger(
        handle="Beta",
        status=RangerStatus.active,
        email=frozenset(["beta@example.com"]),
        onsite=True,
        directoryID=None,
    )


def _position_delta() -> Position:
    return Position(
        positionID="ddd",
        name="Delta",
        members={_ranger_alpha()},
    )


def _team_upsilon() -> Team:
    return Team(
        teamID="uuu",
        name="Upsilon",
        members={_ranger_beta()},
    )


class DMSDirectoryTests(TestCase):
    """
    Tests for :class:`DMSDirectory`
    """

    def test_personnel(self) -> None:
        raise NotImplementedError()

    test_personnel.todo = "unimplemented"  # type: ignore[attr-defined]

    def test_lookupUser(self) -> None:
        def lookup(search: str) -> IMSUser | None:
            return DMSDirectory._lookupUser(
                search,
                (_ranger_alpha(), _ranger_beta()),
                (_position_delta(),),
                (_team_upsilon(),),
            )

        # Case-insensitive matching against handles and email addresses
        self.assertIsNotNone(lookup("alpha"))
        self.assertIsNotNone(lookup("Alpha"))
        self.assertIsNotNone(lookup("beta@example.com"))
        self.assertIsNotNone(lookup("ALPHA@exAMple.com"))

        # Failures to match against handle or email address
        self.assertIsNone(lookup("NotARanger@example.com"))
        self.assertIsNone(lookup("BetaWithSuffix"))

        # Now check the various fields that come back, including
        # positions and teams set up at the top of this test file.
        alpha = lookup("alpha")
        beta = lookup("BETA@EXAMPLE.COM")
        self.assertIsNotNone(alpha)
        # to appease mypy
        assert alpha is not None
        self.assertEqual(alpha.uid, "Alpha")
        self.assertEqual(alpha.shortNames, ("Alpha",))
        self.assertEqual(alpha.onsite, False)
        self.assertEqual(alpha.groups, ("Delta",))
        self.assertEqual(alpha.teams, ())
        self.assertIsNotNone(beta)
        # to appease mypy
        assert beta is not None
        self.assertEqual(beta.onsite, True)
        self.assertEqual(beta.groups, ())
        self.assertEqual(beta.teams, ("Upsilon",))
