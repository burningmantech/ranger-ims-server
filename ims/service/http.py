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
Incident Management System HTTP support.
"""

__all__ = [
    "HeaderName",
    "ContentType",
]

from functools import wraps

from twisted.python.constants import Values, ValueConstant

from ims import __version__ as version



class HeaderName (Values):
    """
    Header names
    """

    server               = ValueConstant("Server")
    contentType          = ValueConstant("Content-Type")
    etag                 = ValueConstant("ETag")
    incidentNumber       = ValueConstant("Incident-Number")
    incidentReportNumber = ValueConstant("Incident-Report-Number")
    location             = ValueConstant("Location")



class ContentType (Values):
    """
    Content types
    """

    HTML       = ValueConstant("text/html; charset=utf-8")
    XHTML      = ValueConstant("application/xhtml+xml")
    CSS        = ValueConstant("text/css")
    JavaScript = ValueConstant("application/javascript")

    JSON       = ValueConstant("application/json")

    text       = ValueConstant("text/plain; charset=utf-8")

    PNG        = ValueConstant("image/png")



if True:
    _fixedETag = version
else:
    # For debugging, change the ETag on every app start
    from uuid import uuid4
    _fixedETag = uuid4().hex


def fixedETag(f):
    """
    Decorator to add a fixed ETag to static resources.
    We use the IMS version number as the ETag, because they may change with new
    IMS versions, but should are otherwise static.
    """
    @wraps(f)
    def wrapper(self, request, *args, **kwargs):
        request.setHeader(HeaderName.etag.value, _fixedETag)
        return f(self, request, *args, **kwargs)

    return wrapper
