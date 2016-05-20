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
            session = request.getSession()
            request.user = getattr(session, "user", None)

            self.log.debug(
                "Authentication: {request.user}", request=request
            )

            if optional or request.user is not None:
                return f(self, request, *args, **kwargs)

            self.log.debug("Authentication failed")

            return self.redirect(request, self.loginURL, origin=u"o")

        return wrapper
    return decorator


def authorized(authorization):
    """
    Decorator enabling authorization for a Klein route method.

    @param authorization: The authorization required to be considered
        authorized.
    @type authorization: L{FlagConstant}
    """
    def decorator(f):
        @wraps(f)
        @authenticated(optional=False)
        def wrapper(self, request, *args, **kwargs):
            session = request.getSession()
            request.authorization = getattr(session, "authorization", None)

            self.log.debug(
                "Authorization: {request.authorization}", request=request
            )

            if (authorization & request.authorization):
                return f(self, request, *args, **kwargs)

            self.log.debug("Authorization failed")

            return self.redirect(request, self.loginURL, origin=u"o")

        return wrapper
    return decorator



class Authorization(Flags):
    """
    Authorizations
    """

    readIncidents  = FlagConstant()
    writeIncidents = FlagConstant()

Authorization.none = Authorization.readIncidents ^ Authorization.readIncidents
