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
Monkey patch L{twisted.web} logging, which annoyingly doesn't let you log the
username.
"""

from zope.interface import provider
from twisted.web.iweb import IAccessLogFormatter
from twisted.web.http import _escape
import twisted.web.http


__all__ = ()



@provider(IAccessLogFormatter)
def combinedLogFormatter(timestamp, request):
    """
    @return: A combined log formatted log line for the given request.

    @see: L{IAccessLogFormatter}
    """
    referrer = _escape(request.getHeader(b"referer") or b"-")
    agent = _escape(request.getHeader(b"user-agent") or b"-")

    if hasattr(request, "user") and request.user is not None:
        username = request.user.shortNames[0]
        try:
            username = _escape(username)
        except Exception:
            username = _escape(repr(username))
    else:
        username = "-"

    line = (
        u'"%(ip)s" %(user)s - %(timestamp)s "%(method)s %(uri)s %(protocol)s" '
        u'%(code)d %(length)s "%(referrer)s" "%(agent)s"' % dict(
            ip=_escape(request.getClientIP() or b"-"),
            timestamp=timestamp,
            method=_escape(request.method),
            uri=_escape(request.uri),
            protocol=_escape(request.clientproto),
            code=request.code,
            length=request.sentLength or "-",
            referrer=referrer,
            agent=agent,
            user=username,
        )
    )
    return line



def patchCombinedLogFormatter():
    twisted.web.http.combinedLogFormatter = combinedLogFormatter
