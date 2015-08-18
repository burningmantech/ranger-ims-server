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
Server
"""

__all__ = [
    "Resource",
]

if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from zope.interface import provider

from twisted.python.filepath import FilePath
from twisted.cred.checkers import FilePasswordDB
from twisted.web.iweb import IAccessLogFormatter
from twisted.web.http import _escape
import twisted.web.http

from .config import Configuration
from .auth import guard
from .protocol import ReadWriteIncidentManagementSystem



def loadConfig():
    configFile = (
        FilePath(__file__).parent().parent().child("conf").child("imsd.conf")
    )
    return Configuration(configFile)


def Resource():
    config = loadConfig()
    return guard(
        lambda: ReadWriteIncidentManagementSystem(config),
        "Ranger Incident Management System",
        (
            FilePasswordDB(config.UserDB.path),
        ),
    )



#
# Monkey patch twisted.web logging, which annoyingly doesn't let you log the
# username.
#
@provider(IAccessLogFormatter)
def combinedLogFormatter(timestamp, request):
    """
    @return: A combined log formatted log line for the given request.

    @see: L{IAccessLogFormatter}
    """
    referrer = _escape(request.getHeader(b"referer") or b"-")
    agent = _escape(request.getHeader(b"user-agent") or b"-")

    if hasattr(request, b"user") and request.user:
        try:
            user = _escape(request.user)
        except Exception:
            user = _escape(repr(request.user))
    else:
        user = b"-"

    line = (
        u'"%(ip)s" %(user)s - %(timestamp)s "%(method)s %(uri)s %(protocol)s" '
        u'%(code)d %(length)s "%(referrer)s" "%(agent)s"' % dict(
            ip=_escape(request.getClientIP() or b"-"),
            timestamp=timestamp,
            method=_escape(request.method),
            uri=_escape(request.uri),
            protocol=_escape(request.clientproto),
            code=request.code,
            length=request.sentLength or u"-",
            referrer=referrer,
            agent=agent,
            user=user,
        )
    )
    return line

twisted.web.http.combinedLogFormatter = combinedLogFormatter


if __name__ == "__main__":
    print loadConfig()
