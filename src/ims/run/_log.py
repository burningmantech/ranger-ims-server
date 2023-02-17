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

import twisted.web.http
from twisted.web.http import _escape
from twisted.web.iweb import IAccessLogFormatter, IRequest
from zope.interface import provider


__all__ = ("patchCombinedLogFormatter",)


@provider(IAccessLogFormatter)
def combinedLogFormatter(timestamp: str, request: IRequest) -> str:
    """
    @return: A combined log formatted log line for the given request.

    @see: L{IAccessLogFormatter}
    """
    referrer = _escape(request.getHeader("referer") or "-")
    agent = _escape(request.getHeader("user-agent") or "-")

    clientIP = request.getClientIP()

    forwardedFor = (
        request.requestHeaders.getRawHeaders(b"x-forwarded-for", [b""])[0]
        .split(b",")[0]
        .strip()
    ).decode("charmap")

    if forwardedFor:
        ip = f"{forwardedFor} > {clientIP}"
    else:
        ip = clientIP

    if hasattr(request, "user") and request.user is not None:
        username = request.user.shortNames[0]
        try:
            username = _escape(username)
        except Exception:
            username = _escape(repr(username))
    else:
        username = "-"

    line = (
        '"{ip}" {user} - {timestamp} "{method} {uri} {protocol}" '
        '{code} {length} "{referrer}" "{agent}"'.format(
            ip=_escape(ip or "-"),
            timestamp=timestamp,
            method=_escape(request.method),
            uri=_escape(request.uri),
            protocol=_escape(request.clientproto),  # type: ignore[attr-defined]
            code=request.code,  # type: ignore[attr-defined]
            length=request.sentLength or "-",  # type: ignore[attr-defined]
            referrer=referrer,
            agent=agent,
            user=username,
        )
    )
    return line


def patchCombinedLogFormatter() -> None:
    """
    Patch the twisted.web.http.combinedLogFormatter to include USER.
    """
    twisted.web.http.combinedLogFormatter = combinedLogFormatter
