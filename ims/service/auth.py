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
Incident Management System authorization and authentication.
"""

__all__ = [
    "authenticated",
    "authorized",
]

from functools import wraps

from twisted.python.constants import FlagConstant, Flags



class Authorization(Flags):
    """
    Authorizations
    """

    readIncidents  = FlagConstant()
    writeIncidents = FlagConstant()

Authorization.none = Authorization.readIncidents ^ Authorization.readIncidents



def authenticated(optional=False):
    """
    Decorator enabling authentication for a Klein route method.

    The route method will be called if the request is authenticated.
    If the request is not authenticated, the client will be redirected to the
    login page.

    @param optional: If C{True}, the route will be called even if the request
        has no authentication, in which case C{request.user} is C{None}.
    @type optional: L{bool}
    """
    def decorator(f):
        @wraps(f)
        def wrapper(self, request, *args, **kwargs):
            if self.authenticateRequest(request) or optional:
                return f(self, request, *args, **kwargs)
            else:
                return self.redirect(request, self.loginURL, origin=u"o")

        return wrapper
    return decorator


def authorized(requiredAuthorizations=Authorization.none):
    """
    Decorator enabling authorization for a Klein route method.

    @param requiredAuthorizations: The authorizations required to be considered
        authorized.
    @type requiredAuthorizations: L{FlagConstant}
    """
    def decorator(f):
        @wraps(f)
        @authenticated(optional=False)
        def wrapper(self, request, *args, **kwargs):
            if self.authorizeRequest(request, None, requiredAuthorizations):
                return f(self, request, *args, **kwargs)
            else:
                return self.redirect(request, self.loginURL, origin=u"o")

        return wrapper
    return decorator
