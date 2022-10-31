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
Incident Management System web application authentication endpoints.
"""

from collections.abc import Iterable
from hashlib import sha256

from twisted.logger import Logger
from twisted.web.iweb import IRequest

from ims.ext.klein import ContentType, HeaderName


__all__ = ()


log = Logger()


#
# MIME type wrappers
#


def jsonBytes(request: IRequest, data: bytes, etag: str | None = None) -> bytes:
    """
    Respond with encoded JSON text.
    """
    request.setHeader(HeaderName.contentType.value, ContentType.json.value)
    if etag is None:
        etag = sha256(data).hexdigest()
    request.setHeader(HeaderName.etag.value, etag)
    return data


def writeJSONStream(
    request: IRequest,
    jsonStream: Iterable[bytes],
    etag: str | None = None,
) -> None:
    """
    Respond with a stream of JSON data.
    """
    request.setHeader(HeaderName.contentType.value, ContentType.json.value)
    if etag is not None:
        request.setHeader(HeaderName.etag.value, etag)
    for line in jsonStream:
        request.write(line)


def buildJSONArray(items: Iterable[bytes]) -> Iterable[bytes]:
    """
    Generate a JSON array from an iterable of bytes.
    """
    first = True

    yield b"["

    for item in items:
        if first:
            first = False
        else:
            yield b","

        yield item

    yield b"]"
