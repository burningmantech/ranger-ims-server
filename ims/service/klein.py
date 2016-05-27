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
]

from functools import wraps

from twisted.internet.defer import inlineCallbacks, returnValue

from klein import Klein

from ims import __version__ as version
from ..dms import DatabaseError
from .http import HeaderName
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
            except (NotAuthenticatedError, NotAuthorizedError):
                returnValue(self.redirect(request, self.loginURL, origin=u"o"))
            except DatabaseError as e:
                self.log.error("DMS error: {failure}", failure=e)
            except Exception:
                self.log.failure("Request failed")
            else:
                returnValue(response)

            returnValue(self.internalErrorResource(request))

        return wrapper
    return decorator
