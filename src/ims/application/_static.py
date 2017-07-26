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

from hashlib import sha1
from typing import Any, Iterable, Optional
from typing.io import BinaryIO

from twisted.logger import Logger
from twisted.python.filepath import FilePath
from twisted.web.iweb import IRequest

import ims.legacy.element
from ims.ext.klein import ContentType, HeaderName, KleinRenderable

from ._klein import notFoundResponse


__all__ = ()


log = Logger()


#
# MIME type wrappers
#

def styleSheet(
    request: IRequest, name: str, *names: str
) -> KleinRenderable:
    """
    Respond with a style sheet.
    """
    request.setHeader(HeaderName.contentType.value, ContentType.css.value)
    return builtInResource(request, name, *names)


def javaScript(
    request: IRequest, name: str, *names: str
) -> KleinRenderable:
    """
    Respond with JavaScript.
    """
    request.setHeader(
        HeaderName.contentType.value, ContentType.javascript.value
    )
    return builtInResource(request, name, *names)


def jsonBytes(
    request: IRequest, data: bytes, etag: Optional[str] = None
) -> bytes:
    """
    Respond with encoded JSON text.
    """
    request.setHeader(HeaderName.contentType.value, ContentType.json.value)
    if etag is None:
        etag = sha1(data).hexdigest()
    request.setHeader(HeaderName.etag.value, etag)
    return data


def writeJSONStream(
    request: IRequest, jsonStream: BinaryIO,
    etag: Optional[str] = None,
) -> None:
    """
    Respond with a stream of JSON data.
    """
    request.setHeader(HeaderName.contentType.value, ContentType.json.value)
    if etag is not None:
        request.setHeader(HeaderName.etag.value, etag)
    for line in jsonStream:
        request.write(line)


def buildJSONArray(items: Iterable[Any]) -> Iterable[bytes]:
    """
    Generate a JSON array from an iterable of JSON objects.
    """
    first = True

    yield b'['

    for item in items:
        if first:
            first = False
        else:
            yield b","

        yield item

    yield b']'


#
# File access
#

_resourcesDirectory = FilePath(ims.legacy.element.__file__).parent()

def builtInResource(
    request: IRequest, name: str, *names: str
) -> KleinRenderable:
    """
    Respond with data from a local file.
    """
    filePath = _resourcesDirectory.child(name)

    for name in names:
        filePath = filePath.child(name)

    try:
        return filePath.getContent()
    except IOError:
        log.error(
            "File not found: {filePath.path}", filePath=filePath
        )
        return notFoundResponse(request)
