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

from twisted.logger import Logger
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.web import http

from klein import Klein

from ims import __version__ as version
from ..dms import DMSError
from ..element.redirect import RedirectPage
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
            try:
                response = yield f(self, request, *args, **kwargs)
            except NotAuthenticatedError:
                returnValue(self.redirect(request, self.loginURL, origin=u"o"))
            except NotAuthorizedError:
                returnValue(self.notAuthorizedResource(request))
            except DMSError as e:
                self.log.error("DMS error: {failure}", failure=e)
            except Exception:
                self.log.failure("Request failed")
            else:
                returnValue(response)

            returnValue(self.internalErrorResource(request))

        return wrapper
    return decorator



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
        request.setResponseCode(http.NOT_FOUND)
        return self.textResource(request, "Not found.")


    def notAuthorizedResource(self, request):
        request.setResponseCode(http.NOT_ALLOWED)
        return b"Permission denied"


    def invalidQueryResource(self, request, arg, value):
        request.setResponseCode(http.BAD_REQUEST)
        return self.textResource(
            request, "Invalid query: {}={}".format(arg, value)
        )


    def badRequestResource(self, request, message=None):
        request.setResponseCode(http.BAD_REQUEST)
        if message is None:
            message = "Bad request."
        else:
            message = u"{}".format(message).encode("utf-8")
        return self.textResource(request, message)


    def internalErrorResource(self, request, message=None):
        request.setResponseCode(http.INTERNAL_SERVER_ERROR)
        if message is None:
            message = "Internal error."
        else:
            message = u"{}".format(message).encode("utf-8")
        return self.textResource(request, message)
