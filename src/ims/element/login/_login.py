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
Login page.
"""

from twisted.web.iweb import IRequest
from twisted.web.template import Tag, renderer, tags

from ims.ext.klein import KleinRenderable

from .._element import Page


__all__ = ()



class LoginPage(Page):
    """
    Login page.
    """

    def __init__(self, urls: type, failed: bool = False) -> None:
        super().__init__(urls=urls, title="Log In")
        self.failed = failed


    @renderer
    def if_authn_failed(
        self, request: IRequest, tag: Tag = tags.div
    ) -> KleinRenderable:
        """
        Render conditionally if the user failed to authenticate.
        """
        if self.failed:
            return tag
        else:
            return ""


    @renderer
    def if_authz_failed(
        self, request: IRequest, tag: Tag = tags.div
    ) -> KleinRenderable:
        """
        Render conditionally if the user failed to authorize.
        """
        if self.failed:
            # authn failed, not authz
            return ""

        session = request.getSession()
        user = getattr(session, "user", None)

        if user is None:
            return ""

        # We have a user but still got sent to login page
        return tag
