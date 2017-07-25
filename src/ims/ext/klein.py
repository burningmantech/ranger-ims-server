# -*- test-case-name: ranger-ims-server.ext.test.test_klein -*-
"""
Extensions to :mod:`klein`
"""

from enum import Enum
from functools import wraps
from typing import Any, Awaitable, Callable, Union

from twisted.web.iweb import IRenderable, IRequest
from twisted.web.resource import IResource

from .. import __version__ as version


__all__ = (
    "ContentType",
    "HeaderName",
    "KleinRenderable",
    "KleinRouteMethod",
    "Method",
    "static",
)


# Expected return types for route methods
KleinRenderable = Union[str, IResource, IRenderable]
KleinRouteMethod = Callable[
    ..., Union[KleinRenderable, Awaitable[KleinRenderable]]
]



class Method(Enum):
    """
    HTTP methods.
    """

    # HTTP 1.0
    GET = "GET"
    POST = "POST"
    HEAD = "HEAD"

    # HTTP 1.1
    OPTIONS = "OPTIONS"
    PUT = "PUT"
    DELETE = "DELETE"
    TRACE = "TRACE"
    CONNECT = "CONNECT"

    # RFC 5789
    PATCH = "PATCH"

    # WebDAV
    COPY = "COPY"
    LOCK = "LOCK"
    MKCOL = "MKCOL"
    MOVE = "MOVE"
    PROPFIND = "PROPFIND"
    PROPPATCH = "PROPPATCH"
    UNLOCK = "UNLOCK"



class ContentType(Enum):
    """
    MIME content types.
    """

    css = "text/css"
    eventStream = "text/event-stream"
    html = "text/html"
    javascript = "application/javascript"
    json = "application/json"
    png = "image/png"
    text = "text/plain"
    xhtml = "application/xhtml+xml"



class HeaderName(Enum):
    """
    HTTP header names.
    """

    server = "Server"
    cacheControl = "Cache-Control"
    contentType = "Content-Type"
    etag = "ETag"
    location = "Location"



if True:
    _staticETag = version
    _maxAge = 60 * 5  # 5 minutes
else:
    # For debugging, change the ETag on app launch
    from uuid import uuid4
    _staticETag = uuid4().hex
    _maxAge = 0

_cacheControl = "max-age={}".format(_maxAge)


def static(f: KleinRouteMethod) -> KleinRouteMethod:
    """
    Decorate a route handler to add fixed ETag and Cache-Control headers, which
    are appropriate for static resources.
    """
    @wraps(f)
    def wrapper(
        self: Any, request: IRequest, *args: Any, **kwargs: Any
    ) -> KleinRenderable:
        def setHeader(name: HeaderName, value: str) -> None:
            request.setHeader(name.value, value)

        setHeader(HeaderName.etag, _staticETag)
        setHeader(HeaderName.cacheControl, _cacheControl)

        return f(self, request, *args, **kwargs)

    return wrapper
