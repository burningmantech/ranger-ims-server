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

from json import JSONDecodeError
from typing import ClassVar

from attr import attrs

from hyperlink import URL

from twisted.logger import Logger
from twisted.web import http
from twisted.web.iweb import IRequest

from ims.config import Configuration, URLs
from ims.ext.json import jsonTextFromObject, objectFromJSONText
from ims.ext.klein import ContentType, HeaderName, KleinRenderable

from ._klein import (
    Router,
    badRequestResponse,
    invalidJSONResponse,
    invalidQueryResponse,
    queryValue,
    redirect,
)


__all__ = ()


def _unprefix(url: URL) -> URL:
    prefix = URLs.auth.path[:-1]
    assert url.path[: len(prefix)] == prefix, (url.path[len(prefix) :], prefix)
    return url.replace(path=url.path[len(prefix) :])


@attrs(frozen=True, auto_attribs=True, kw_only=True, eq=False)
class AuthApplication:
    """
    Application with login and logout endpoints.
    """

    _log: ClassVar[Logger] = Logger()
    router: ClassVar[Router] = Router()

    config: Configuration

    @router.route(_unprefix(URLs.auth), methods=("POST",))
    async def auth(self, request: IRequest) -> KleinRenderable:
        """
        Authentication endpoint.
        """
        contentType = request.getHeader(HeaderName.contentType.value)

        if contentType != ContentType.json.value:
            return badRequestResponse(
                request, f"Unsupported request Content-Type: {contentType}"
            )

        body = request.content.read()
        try:
            json = objectFromJSONText(body.decode("utf-8"))
        except JSONDecodeError as e:
            return invalidJSONResponse(request, e)

        username = json.get("identification")
        password = json.get("password")

        if username is None:
            return badRequestResponse(request, "Missing identification.")

        if password is None:
            return badRequestResponse(request, "Missing password.")

        user = await self.config.directory.lookupUser(username)

        if user is None:
            self._log.debug(
                "Login failed: no such user: {username}", username=username
            )
        else:
            authProvider = self.config.authProvider
            authenticated = await authProvider.verifyPassword(
                user, password
            )
            if not authenticated:
                self._log.debug(
                    "Login failed: incorrect credentials for user: {user}",
                    user=user,
                )

            else:
                return await authProvider.authorizationForUser(user)

        request.setResponseCode(http.UNAUTHORIZED)
        return jsonTextFromObject(dict(status="invalid-credentials"))

    @router.route(_unprefix(URLs.login), methods=("HEAD", "GET"))
    def login(self, request: IRequest, failed: bool = False) -> KleinRenderable:
        """
        Endpoint for the login page.
        """
        self.config.authProvider.authenticateRequest(request, optional=True)

        from ims.element.login import LoginPage

        return LoginPage(config=self.config, failed=failed)

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
            user = await self.config.directory.lookupUser(username)

        if user is None:
            self._log.debug(
                "Login failed: no such user: {username}", username=username
            )
        else:
            if password is None:
                return invalidQueryResponse(request, "password")

            authenticated = await self.config.authProvider.verifyPassword(
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
                    user=user,
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
