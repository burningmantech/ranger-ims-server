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

from twisted.python.filepath import FilePath
from twisted.cred.checkers import FilePasswordDB

from .config import Configuration
from .auth import guard
from .protocol import IncidentManagementSystem



def loadConfig():
    configFile = (
        FilePath(__file__).parent().parent().child("conf").child("imsd.conf")
    )
    return Configuration(configFile)


def Resource():
    config = loadConfig()
    return guard(
        lambda: IncidentManagementSystem(config),
        "Ranger Incident Management System",
        (
            FilePasswordDB(config.UserDB.path),
        ),
    )


# # Monkey patch twisted.web logging, which annoyingly doesn't let you log the
# # username.
# def logAccess(self, request):
#     if hasattr(self, "logFile"):
#         if hasattr(request, "user") and request.user:
#             user = self._escape(request.user)
#         else:
#             user = "-"

#         line = (
#             '{ip} {user} - {time} '
#             '"{method} {uri} {proto}" '
#             '{status} {length} '
#             '"{referer}" "{agent}"'
#             '\n'
#         ).format(
#             ip=request.getClientIP(),
#             user=user,
#             time=self._logDateTime,
#             method=self._escape(request.method),
#             uri=self._escape(request.uri),
#             proto=self._escape(request.clientproto),
#             status=request.code,
#             length=request.sentLength or "-",
#             referer=self._escape(request.getHeader("referer") or "-"),
#             agent=self._escape(request.getHeader("user-agent") or "-"),
#         )
#         self.logFile.write(line)

# import twisted.web.http
# twisted.web.http.HTTPFactory.log = logAccess



if __name__ == "__main__":
    print loadConfig()
