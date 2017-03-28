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
Incident Management System Klein application.
"""

from __future__ import absolute_import

__all__ = [
    "application",
    "route",
    "KleinService",
]

from functools import wraps

from twisted.python.url import URL
from twisted.logger import Logger
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.web import http
from twisted.web.iweb import IRenderable
from twisted.web.template import renderElement

from werkzeug.routing import RequestRedirect
from werkzeug.exceptions import NotFound, MethodNotAllowed
from klein import Klein

from ims import __version__ as version
from ..element.redirect import RedirectPage
from .urls import URLs
from ..dms import DMSError
from .http import HeaderName, ContentType
from .error import NotAuthenticatedError, NotAuthorizedError



application = Klein()


def route(*args, **kwargs):
    """
    Decorator that applies a Klein route and anything else we want applied to
    all endpoints.
    """
    def decorator(f):
        @application.route(*args, **kwargs)
        @wraps(f)
        @inlineCallbacks
        def wrapper(self, request, *args, **kwargs):
            request.setHeader(
                HeaderName.server.value,
                "Incident Management System/{}".format(version),
            )

            # Capture authentication info if sent by the client, (ie. it's been
            # previously asked to authenticate), so we can log it, but don't
            # require authentication.
            self.authenticateRequest(request, optional=True)

            response = yield f(self, request, *args, **kwargs)
            returnValue(response)

        return wrapper
    return decorator


def renderResponse(f):
    """
    Decorator to ensure that the returned response is rendered, if applicable.
    Needed because L{Klein.handle_errors} doesn't do rendering for you.
    """
    @wraps(f)
    def wrapper(self, request, *args, **kwargs):
        response = f(self, request, *args, **kwargs)

        if IRenderable.providedBy(response):
            return renderElement(request, response)

        return response

    return wrapper



class KleinService(object):
    """
    Klein service.
    """

    log = Logger()
    app = application

    def resource(self):
        return self.app.resource()


    def redirect(self, request, location, origin=None):
        if origin is not None:
            location = location.set(origin, request.uri.decode("utf-8"))

        url = location.asText().encode("utf-8")

        request.setHeader(HeaderName.contentType.value, ContentType.HTML.value)
        request.setHeader(HeaderName.location.value, url)
        request.setResponseCode(http.FOUND)

        return RedirectPage(self, location)


    #
    # Query arguments
    #

    def queryValue(self, request, name, default=None):
        """
        Look up the value of a query parameter with the given name in the
        given request.

        @param request: The request to look into.
        @type request: L{IRequest}

        @param name: The name of the query parameter to find a value for.
        @type name: L{unicode}

        @param default: The default value to return if no query parameter
            specified by C{name} is found in C{request}.
        @type default: L{unicode}

        @return: The value of the query parameter specified by C{name}, or
            C{default} if there no such query parameter.  If more than one value
            is found, return the last value found.
        @rtype: L{unicode}
        """
        values = request.args.get(name.encode("utf-8"))

        if values is None:
            return default

        if len(values) > 0:
            return values[-1].decode("utf-8")
        else:
            return default


    def queryValues(self, request, name, default=()):
        """
        Look up the values of a query parameter with the given name in the
        given request.

        @param request: The request to look into.
        @type request: L{IRequest}

        @param name: The name of the query parameter to find a value for.
        @type name: L{unicode}

        @param default: The default values to return if no query parameter
            specified by C{name} is found in C{request}.
        @type default: iterable of L{unicode}

        @return: The values of the query parameter specified by C{name}, or
            C{default} if there no such query parameter.
        @rtype: iterable of L{unicode}
        """
        values = request.args.get(name)

        if values is None:
            return default

        return (a.decode("utf-8") for a in values)


    #
    # Error resources
    #

    def noContentResource(self, request, etag=None):
        request.setResponseCode(http.NO_CONTENT)
        if etag is not None:
            request.setHeader(HeaderName.etag.value, etag)
        return b""


    def textResource(self, request, message):
        message = message
        request.setHeader(HeaderName.contentType.value, ContentType.text.value)
        request.setHeader(HeaderName.etag.value, bytes(hash(message)))
        return message.encode("utf-8")


    def notFoundResource(self, request):
        self.log.debug("Resource not found: {request.uri}", request=request)

        # Require authentication.
        # This is because exposing what resources do or do not exist can expose
        # information that was not meant to be exposed.
        self.authenticateRequest(request)
        request.setResponseCode(http.NOT_FOUND)
        return self.textResource(request, "Not found")


    def methodNotAllowedResource(self, request):
        self.log.debug(
            "Method {request.method} not allowed for resource: {request.uri}",
            request=request
        )

        # Require authentication.
        # This is because exposing what resources do or do not exist can expose
        # information that was not meant to be exposed.
        self.authenticateRequest(request)
        request.setResponseCode(http.NOT_ALLOWED)
        return self.textResource(request, "HTTP method not allowed")


    def forbiddenResource(self, request):
        user = getattr(request, "user", None)
        self.log.debug(
            "Forbidden resource for user {user}: {request.uri}",
            request=request, user=user
        )

        request.setResponseCode(http.FORBIDDEN)
        return self.textResource(request, "Permission denied")


    def badRequestResource(self, request, message=None):
        self.log.debug(
            "Bad request for resource: {request.uri}: {message}",
            request=request, message=message
        )

        request.setResponseCode(http.BAD_REQUEST)
        if message is None:
            message = "Bad request"
        else:
            message = "{}".format(message).encode("utf-8")
        return self.textResource(request, message)


    def invalidQueryResource(self, request, arg, value):
        if value is None:
            return self.badRequestResource(
                request, "Invalid query: missing parameter {}".format(arg)
            )
        else:
            return self.badRequestResource(
                request, "Invalid query: {}={}".format(arg, value)
            )


    def internalErrorResource(self, request, message=None):
        self.log.critical(
            "Internal error for resource: {request.uri}: {message}",
            request=request, message=message
        )

        request.setResponseCode(http.INTERNAL_SERVER_ERROR)
        if message is None:
            message = "Internal error"
        else:
            message = "{}".format(message).encode("utf-8")
        return self.textResource(request, message)


    #
    # Error handlers
    #

    @app.handle_errors(RequestRedirect)
    @renderResponse
    def requestRedirectError(self, request, failure):
        """
        Redirect.
        """
        url = URL.fromText(failure.value.args[0].decode("utf-8"))
        return self.redirect(request, url)


    @app.handle_errors(NotFound)
    @renderResponse
    def notFoundError(self, request, failure):
        """
        Not found.
        """
        return self.notFoundResource(request)


    @app.handle_errors(MethodNotAllowed)
    @renderResponse
    def methodNotAllowedError(self, request, failure):
        """
        HTTP method not allowed.
        """
        return self.methodNotAllowedResource(request)


    @app.handle_errors(NotAuthorizedError)
    @renderResponse
    def notAuthorizedError(self, request, failure):
        """
        Not authorized.
        """
        return self.forbiddenResource(request)


    @app.handle_errors(NotAuthenticatedError)
    @renderResponse
    def notAuthenticatedError(self, request, failure):
        """
        Not authenticated.
        """
        element = self.redirect(request, URLs.login, origin="o")
        return renderElement(request, element)


    @app.handle_errors(DMSError)
    @renderResponse
    def dmsError(self, request, failure):
        """
        DMS error.
        """
        self.log.failure("DMS error", failure)
        return self.internalErrorResource(request)


    @app.handle_errors
    @renderResponse
    def unknownError(self, request, failure):
        """
        Deal with a request error caught by Klein.
        """
        # This logs the failure traceback for debugging.
        # Klein normally will also display the traceback in the response.
        # We don't do that for a few reasons:
        #  - It's a poor security practice to explain to an attacker what
        #    exactly is causing an internal error.
        #  - Most users don't know what to do with that inforrmation.
        #  - The admins should be able to find the errors in the logs.
        #  - Klein doing that is a developer feature; developers can also watch
        #    the logs.
        #  - The traceback is emitted after whatever else was sent with the
        #    request, which often means that it displays like a total mess in
        #    a browser, and that's just pitiful.
        self.log.failure("Request failed", failure)
        return self.internalErrorResource(request)
