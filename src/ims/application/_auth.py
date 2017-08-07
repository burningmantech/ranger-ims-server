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
Incident Management System web application authentication endpoints.
"""

from attr import attrib, attrs
from attr.validators import instance_of

from hyperlink import URL

from twisted.logger import Logger
from twisted.web.iweb import IRequest

from ims.auth import AuthProvider
from ims.config import Configuration, URLs
from ims.ext.klein import KleinRenderable

from ._klein import Router, invalidQueryResponse, queryValue, redirect


__all__ = ()


def _unprefix(url: URL) -> URL:
    prefix = URLs.auth.path[:-1]
    assert url.path[:len(prefix)] == prefix, (url.path[len(prefix):], prefix)
    return url.replace(path=url.path[len(prefix):])



@attrs(frozen=True)
class AuthApplication(object):
    """
    Application with login and logout endpoints.
    """

    _log = Logger()
    router = Router()


    auth: AuthProvider = attrib(validator=instance_of(AuthProvider))
    config: Configuration = attrib(validator=instance_of(Configuration))


    @router.route(_unprefix(URLs.login), methods=("HEAD", "GET"))
    def login(
        self, request: IRequest, failed: bool = False
    ) -> KleinRenderable:
        """
        Endpoint for the login page.
        """
        self.auth.authenticateRequest(request, optional=True)

        from ims.element.login import LoginPage
        return LoginPage(self.config, failed=failed)


    @router.route(_unprefix(URLs.login), methods=("POST",))
    async def loginSubmit(self, request: IRequest) -> KleinRenderable:
        """
        Endpoint for a login form submission.
        """
        username = queryValue(request, "username")
        password = queryValue(request, "password", default="")

        if username is None:
            user = None
        else:
            user = await self.auth.lookupUserName(username)

        if user is None:
            self._log.debug(
                "Login failed: no such user: {username}", username=username
            )
        else:
            if password is None:
                return invalidQueryResponse(request, "password")

            authenticated = await self.auth.verifyCredentials(
                user, password
            )

            if authenticated:
                session = request.getSession()
                session.user = user

                url = queryValue(request, "o")
                if url is None:
                    location = URLs.app  # Default to application home
                else:
                    location = URL.fromText(url)

                return redirect(request, location)
            else:
                self._log.debug(
                    "Login failed: incorrect credentials for user: {user}",
                    user=user
                )

        return self.login(request, failed=True)


    @router.route(_unprefix(URLs.logout), methods=("HEAD", "GET"))
    def logout(self, request: IRequest) -> KleinRenderable:
        """
        Endpoint for logging out.
        """
        session = request.getSession()
        session.expire()

        # Redirect back to application home
        return redirect(request, URLs.app)
