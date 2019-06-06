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
Tests for L{ims.auth._provider}.
"""

from hypothesis import given

from ims.ext.trial import TestCase
from ims.model import Ranger
from ims.model.strategies import rangers

from .._provider import Authorization, User


__all__ = ()



class AuthorizationTests(TestCase):
    """
    Tests for :class:`Authorization`
    """

    def test_authorization_none(self) -> None:
        for authorization in Authorization:
            if authorization is Authorization.none:
                continue
            self.assertNotIn(authorization, Authorization.none)


    def test_authorization_all(self) -> None:
        for authorization in Authorization:
            self.assertIn(authorization, Authorization.all)



class UserTests(TestCase):
    """
    Tests for :class:`User`
    """

    @given(rangers())
    def test_shortNames_handle(self, ranger: Ranger) -> None:
        user = User(ranger=ranger, groups=())
        self.assertIn(ranger.handle, user.shortNames)


    @given(rangers())
    def test_hashedPassword(self, ranger: Ranger) -> None:
        user = User(ranger=ranger, groups=())
        self.assertEqual(user.hashedPassword, ranger.password)


    @given(rangers())
    def test_active(self, ranger: Ranger) -> None:
        user = User(ranger=ranger, groups=())
        self.assertEqual(user.active, ranger.onSite)


    @given(rangers())
    def test_rangerHandle(self, ranger: Ranger) -> None:
        user = User(ranger=ranger, groups=())
        self.assertEqual(user.rangerHandle, ranger.handle)


    @given(rangers())
    def test_str(self, ranger: Ranger) -> None:
        user = User(ranger=ranger, groups=())
        self.assertEqual(str(user), str(ranger))
