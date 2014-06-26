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
Protocol utilities
"""

__all__ = [
    "url_for",
    "set_response_header",
    "http_sauce",
    "HeaderName",
    "ContentType",
]

from functools import wraps

from twisted.python import log
from twisted.python.constants import Values, ValueConstant
from twisted.web import http

from klein.interfaces import IKleinRequest

from .data import InvalidDataError
from .store import NoSuchIncidentError
from .dms import DatabaseError



def url_for(request, endpoint, *args, **kwargs):
    kwargs["force_external"] = True
    return IKleinRequest(request).url_for(endpoint, *args, **kwargs)


def set_response_header(request, name, value):
    if isinstance(value, ValueConstant):
        value = value.value
    request.setHeader(name.value, value)


def set_user_agent(request):
    # Get User-Agent
    values = request.requestHeaders.getRawHeaders(
        HeaderName.userAgent.value, []
    )
    for value in values:
        if value:
            request.userAgent = value
            break
    else:
        request.userAgent = None


def set_accepts(request):
    # Get accept header
    accepts = []
    values = request.requestHeaders.getRawHeaders(
        HeaderName.accept.value, []
    )
    for value in values:
        for media_type in value.split(","):
            if ";" in media_type:
                (mime_type, parameter) = media_type.split(";")
            else:
                mime_type = media_type
            try:
                accepts.append(ContentType.lookupByValue(mime_type))
            except ValueError:
                pass
    request.accepts = accepts


def http_sauce(f):
    @wraps(f)
    def wrapper(self, request, *args, **kwargs):
        set_user_agent(request)
        set_accepts(request)

        # Reject requests with disallowed User-Agent strings
        for expression in self.config.RejectClientsRegex:
            if expression.match(request.userAgent):
                log.msg("Rejected user agent: {0}".format(request.userAgent))
                request.setResponseCode(http.FORBIDDEN)
                set_response_header(
                    request, HeaderName.contentType, ContentType.plain
                )
                return "Client software not allowed.\n"

        # Store user name
        request.user = self.avatarId

        try:
            return f(self, request, *args, **kwargs)

        except NoSuchIncidentError as e:
            request.setResponseCode(http.NOT_FOUND)
            set_response_header(
                request, HeaderName.contentType, ContentType.plain
            )
            return "No such incident: {0}\n".format(e)

        except InvalidDataError as e:
            log.err(e)
            request.setResponseCode(http.BAD_REQUEST)
            set_response_header(
                request, HeaderName.contentType, ContentType.plain
            )
            return "Invalid data: {0}\n".format(e)

        except DatabaseError as e:
            log.err(e)
            request.setResponseCode(http.INTERNAL_SERVER_ERROR)
            set_response_header(
                request, HeaderName.contentType, ContentType.plain
            )
            return "Database error."

        except Exception as e:
            log.err(e)
            request.setResponseCode(http.INTERNAL_SERVER_ERROR)
            set_response_header(
                request, HeaderName.contentType, ContentType.plain
            )
            return "Server error.\n"

    return wrapper



class HeaderName (Values):
    contentType    = ValueConstant("Content-Type")
    etag           = ValueConstant("ETag")
    incidentNumber = ValueConstant("Incident-Number")
    location       = ValueConstant("Location")
    userAgent      = ValueConstant("User-Agent")
    accept         = ValueConstant("Accept")



class ContentType (Values):
    HTML  = ValueConstant("text/html")
    JSON  = ValueConstant("application/json")
    XHTML = ValueConstant("application/xhtml+xml")
    plain = ValueConstant("text/plain")
