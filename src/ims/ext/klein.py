# -*- test-case-name: ranger-ims-server.ext.test.test_klein -*-
"""
Extensions to :mod:`klein`
"""

from functools import wraps
from typing import Any, Awaitable, Callable, Union

from twisted.web.iweb import IRenderable, IRequest
from twisted.web.resource import IResource
from twisted.web.template import Tag

from ims.ext.enum import Enum, Names, auto

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
KleinRenderable = Union[str, bytes, IResource, IRenderable, Tag]
KleinRouteMethod = Callable[
    ..., Union[KleinRenderable, Awaitable[KleinRenderable]]
]


class Method(Names):
    """
    HTTP methods.
    """

    # HTTP 1.0
    GET = auto()
    POST = auto()
    HEAD = auto()

    # HTTP 1.1
    OPTIONS = auto()
    PUT = auto()
    DELETE = auto()
    TRACE = auto()
    CONNECT = auto()

    # RFC 5789
    PATCH = "PATCH"

    # WebDAV
    COPY = auto()
    LOCK = auto()
    MKCOL = auto()
    MOVE = auto()
    PROPFIND = auto()
    PROPPATCH = auto()
    UNLOCK = auto()


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


if False:
    _staticETag = version  # type: ignore[misc] # unreachable
    _maxAge = 60 * 5  # 5 minutes
else:
    # For debugging, change the ETag on app launch
    from uuid import uuid4

    _staticETag = uuid4().hex
    _maxAge = 0

_cacheControl = f"max-age={_maxAge}"


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
