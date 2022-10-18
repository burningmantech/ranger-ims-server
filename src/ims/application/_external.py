# type: ignore

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
Incident Management System cached external resources.
"""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, ClassVar
from zipfile import BadZipfile

from attr import attrs
from hyperlink import URL
from klein import KleinRenderable
from twisted.internet import defer, protocol
from twisted.logger import Logger
from twisted.python.compat import nativeString
from twisted.python.failure import Failure
from twisted.python.util import InsensitiveDict
from twisted.python.zippath import ZipArchive
from twisted.web import error, http
from twisted.web._newclient import _ensureValidMethod, _ensureValidURI
from twisted.web.client import URI, PartialDownloadError
from twisted.web.iweb import IRequest

from ims.config import Configuration, URLs
from ims.ext.klein import ContentType, HeaderName, static

from ._klein import Router, internalErrorResponse, notFoundResponse


__all__ = ("ExternalApplication",)

##
# NOTE:
# THis file copies from old twisted.web.client sources so that we can upgrade
# Twisted without having to rework the code that calls downloadPage.
# This is temporary, since this file will be go away.
# (That code is copyright Twisted Matrix Laboratories.)
###


class HTTPPageGetter(http.HTTPClient):
    """
    Gets a resource via HTTP, then quits.

    Typically used with L{HTTPClientFactory}.  Note that this class does not, by
    itself, do anything with the response.  If you want to download a resource
    into a file, use L{HTTPPageDownloader} instead.

    @ivar _completelyDone: A boolean indicating whether any further requests are
        necessary after this one completes in order to provide a result to
        C{self.factory.deferred}.  If it is C{False}, then a redirect is going
        to be followed.  Otherwise, this protocol's connection is the last one
        before firing the result Deferred.  This is used to make sure the result
        Deferred is only fired after the connection is cleaned up.
    """

    quietLoss = 0
    followRedirect = True
    failed = 0

    _completelyDone = True

    _specialHeaders = {b"host", b"user-agent", b"cookie", b"content-length"}

    def connectionMade(self):
        method = _ensureValidMethod(getattr(self.factory, "method", b"GET"))
        self.sendCommand(method, _ensureValidURI(self.factory.path))
        if self.factory.scheme == b"http" and self.factory.port != 80:
            host = b"%b:%d" % (self.factory.host, self.factory.port)
        elif self.factory.scheme == b"https" and self.factory.port != 443:
            host = b"%b:%d" % (self.factory.host, self.factory.port)
        else:
            host = self.factory.host
        self.sendHeader(b"Host", self.factory.headers.get(b"host", host))
        self.sendHeader(b"User-Agent", self.factory.agent)
        data = getattr(self.factory, "postdata", None)
        if data is not None:
            self.sendHeader(b"Content-Length", b"%d" % (len(data),))

        cookieData = []
        for (key, value) in self.factory.headers.items():
            if key.lower() not in self._specialHeaders:
                # we calculated it on our own
                self.sendHeader(key, value)
            if key.lower() == b"cookie":
                cookieData.append(value)
        for cookie, cookval in self.factory.cookies.items():
            cookieData.append(cookie + b"=" + cookval)
        if cookieData:
            self.sendHeader(b"Cookie", b"; ".join(cookieData))
        self.endHeaders()
        self.headers = {}

        if data is not None:
            self.transport.write(data)

    def handleHeader(self, key, value):
        """
        Called every time a header is received. Stores the header information
        as key-value pairs in the C{headers} attribute.

        @type key: C{str}
        @param key: An HTTP header field name.

        @type value: C{str}
        @param value: An HTTP header field value.
        """
        key = key.lower()
        l = self.headers.setdefault(key, [])  # noqa: E741
        l.append(value)

    def handleStatus(self, version, status, message):
        """
        Handle the HTTP status line.

        @param version: The HTTP version.
        @type version: L{bytes}
        @param status: The HTTP status code, an integer represented as a
            bytestring.
        @type status: L{bytes}
        @param message: The HTTP status message.
        @type message: L{bytes}
        """
        self.version, self.status, self.message = version, status, message
        self.factory.gotStatus(version, status, message)

    def handleEndHeaders(self):
        self.factory.gotHeaders(self.headers)
        m = getattr(
            self,
            "handleStatus_" + nativeString(self.status),
            self.handleStatusDefault,
        )
        m()

    def handleStatus_200(self):
        pass

    handleStatus_201 = lambda self: self.handleStatus_200()  # noqa: E731
    handleStatus_202 = lambda self: self.handleStatus_200()  # noqa: E731

    def handleStatusDefault(self):
        self.failed = 1

    def handleStatus_301(self):
        l = self.headers.get(b"location")  # noqa: E741
        if not l:
            self.handleStatusDefault()
            return
        url = l[0]
        if self.followRedirect:
            self.factory._redirectCount += 1
            if self.factory._redirectCount >= self.factory.redirectLimit:
                err = error.InfiniteRedirection(
                    self.status, b"Infinite redirection detected", location=url
                )
                self.factory.noPage(Failure(err))
                self.quietLoss = True
                self.transport.loseConnection()
                return

            self._completelyDone = False
            self.factory.setURL(url)

            from twisted.internet import reactor

            if self.factory.scheme == b"https":
                from twisted.internet import ssl

                contextFactory = ssl.ClientContextFactory()
                reactor.connectSSL(
                    nativeString(self.factory.host),
                    self.factory.port,
                    self.factory,
                    contextFactory,
                )
            else:
                reactor.connectTCP(
                    nativeString(self.factory.host),
                    self.factory.port,
                    self.factory,
                )
        else:
            self.handleStatusDefault()
            self.factory.noPage(
                Failure(
                    error.PageRedirect(self.status, self.message, location=url)
                )
            )
        self.quietLoss = True
        self.transport.loseConnection()

    def handleStatus_302(self):
        if self.afterFoundGet:
            self.handleStatus_303()
        else:
            self.handleStatus_301()

    def handleStatus_303(self):
        self.factory.method = b"GET"
        self.handleStatus_301()

    def connectionLost(self, reason):
        """
        When the connection used to issue the HTTP request is closed, notify the
        factory if we have not already, so it can produce a result.
        """
        if not self.quietLoss:
            http.HTTPClient.connectionLost(self, reason)
            self.factory.noPage(reason)
        if self._completelyDone:
            # Only if we think we're completely done do we tell the factory that
            # we're "disconnected".  This way when we're following redirects,
            # only the last protocol used will fire the _disconnectedDeferred.
            self.factory._disconnectedDeferred.callback(None)

    def handleResponse(self, response):
        if self.quietLoss:
            return
        if self.failed:
            self.factory.noPage(
                Failure(error.Error(self.status, self.message, response))
            )
        if self.factory.method == b"HEAD":
            # Callback with empty string, since there is never a response
            # body for HEAD requests.
            self.factory.page(b"")
        elif self.length != None and self.length != 0:  # noqa: E711
            self.factory.noPage(
                Failure(
                    PartialDownloadError(self.status, self.message, response)
                )
            )
        else:
            self.factory.page(response)
        # server might be stupid and not close connection. admittedly
        # the fact we do only one request per connection is also
        # stupid...
        self.transport.loseConnection()

    def timeout(self):
        self.quietLoss = True
        self.transport.abortConnection()
        self.factory.noPage(
            defer.TimeoutError(
                "Getting %s took longer than %s seconds."  # noqa: S001
                % (self.factory.url, self.factory.timeout)
            )
        )


class HTTPPageDownloader(HTTPPageGetter):

    transmittingPage = 0

    def handleStatus_200(self, partialContent=0):
        HTTPPageGetter.handleStatus_200(self)
        self.transmittingPage = 1
        self.factory.pageStart(partialContent)

    def handleStatus_206(self):
        self.handleStatus_200(partialContent=1)

    def handleResponsePart(self, data):
        if self.transmittingPage:
            self.factory.pagePart(data)

    def handleResponseEnd(self):
        if self.length:
            self.transmittingPage = 0
            self.factory.noPage(Failure(PartialDownloadError(self.status)))
        if self.transmittingPage:
            self.factory.pageEnd()
            self.transmittingPage = 0
        if self.failed:
            self.factory.noPage(
                Failure(error.Error(self.status, self.message, None))
            )
            self.transport.loseConnection()


class HTTPClientFactory(protocol.ClientFactory):
    """Download a given URL.

    @type deferred: Deferred
    @ivar deferred: A Deferred that will fire when the content has
          been retrieved. Once this is fired, the ivars `status', `version',
          and `message' will be set.

    @type status: bytes
    @ivar status: The status of the response.

    @type version: bytes
    @ivar version: The version of the response.

    @type message: bytes
    @ivar message: The text message returned with the status.

    @type response_headers: dict
    @ivar response_headers: The headers that were specified in the
          response from the server.

    @type method: bytes
    @ivar method: The HTTP method to use in the request.  This should be one of
        OPTIONS, GET, HEAD, POST, PUT, DELETE, TRACE, or CONNECT (case
        matters).  Other values may be specified if the server being contacted
        supports them.

    @type redirectLimit: int
    @ivar redirectLimit: The maximum number of HTTP redirects that can occur
          before it is assumed that the redirection is endless.

    @type afterFoundGet: C{bool}
    @ivar afterFoundGet: Deviate from the HTTP 1.1 RFC by handling redirects
        the same way as most web browsers; if the request method is POST and a
        302 status is encountered, the redirect is followed with a GET method

    @type _redirectCount: int
    @ivar _redirectCount: The current number of HTTP redirects encountered.

    @ivar _disconnectedDeferred: A L{Deferred} which only fires after the last
        connection associated with the request (redirects may cause multiple
        connections to be required) has closed.  The result Deferred will only
        fire after this Deferred, so that callers can be assured that there are
        no more event sources in the reactor once they get the result.
    """

    protocol = HTTPPageGetter

    url = None
    scheme = None
    host = b""
    port = None
    path = None

    def __init__(
        self,
        url,
        method=b"GET",
        postdata=None,
        headers=None,
        agent=b"Twisted PageGetter",
        timeout=0,
        cookies=None,
        followRedirect=True,
        redirectLimit=20,
        afterFoundGet=False,
    ):
        self.followRedirect = followRedirect
        self.redirectLimit = redirectLimit
        self._redirectCount = 0
        self.timeout = timeout
        self.agent = agent
        self.afterFoundGet = afterFoundGet
        if cookies is None:
            cookies = {}
        self.cookies = cookies
        if headers is not None:
            self.headers = InsensitiveDict(headers)
        else:
            self.headers = InsensitiveDict()
        if postdata is not None:
            self.headers.setdefault(b"Content-Length", b"%d" % (len(postdata),))
            # just in case a broken http/1.1 decides to keep connection alive
            self.headers.setdefault(b"connection", b"close")
        self.postdata = postdata
        self.method = _ensureValidMethod(method)

        self.setURL(url)

        self.waiting = 1
        self._disconnectedDeferred = defer.Deferred()
        self.deferred = defer.Deferred()
        # Make sure the first callback on the result Deferred pauses the
        # callback chain until the request connection is closed.
        self.deferred.addBoth(self._waitForDisconnect)
        self.response_headers = None

    def _waitForDisconnect(self, passthrough):
        """
        Chain onto the _disconnectedDeferred, preserving C{passthrough}, so that
        the result is only available after the associated connection has been
        closed.
        """
        self._disconnectedDeferred.addCallback(lambda ignored: passthrough)
        return self._disconnectedDeferred

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.url}>"

    def setURL(self, url):
        _ensureValidURI(url.strip())
        self.url = url
        uri = URI.fromBytes(url)
        if uri.scheme and uri.host:
            self.scheme = uri.scheme
            self.host = uri.host
            self.port = uri.port
        self.path = uri.originForm

    def buildProtocol(self, addr):
        p = protocol.ClientFactory.buildProtocol(self, addr)
        p.followRedirect = self.followRedirect
        p.afterFoundGet = self.afterFoundGet
        if self.timeout:
            from twisted.internet import reactor

            timeoutCall = reactor.callLater(self.timeout, p.timeout)
            self.deferred.addBoth(self._cancelTimeout, timeoutCall)
        return p

    def _cancelTimeout(self, result, timeoutCall):
        if timeoutCall.active():
            timeoutCall.cancel()
        return result

    def gotHeaders(self, headers):
        """
        Parse the response HTTP headers.

        @param headers: The response HTTP headers.
        @type headers: L{dict}
        """
        self.response_headers = headers
        if b"set-cookie" in headers:
            for cookie in headers[b"set-cookie"]:
                if b"=" in cookie:
                    cookparts = cookie.split(b";")
                    cook = cookparts[0]
                    cook.lstrip()
                    k, v = cook.split(b"=", 1)
                    self.cookies[k.lstrip()] = v.lstrip()

    def gotStatus(self, version, status, message):
        """
        Set the status of the request on us.

        @param version: The HTTP version.
        @type version: L{bytes}
        @param status: The HTTP status code, an integer represented as a
            bytestring.
        @type status: L{bytes}
        @param message: The HTTP status message.
        @type message: L{bytes}
        """
        self.version, self.status, self.message = version, status, message

    def page(self, page):
        if self.waiting:
            self.waiting = 0
            self.deferred.callback(page)

    def noPage(self, reason):
        if self.waiting:
            self.waiting = 0
            self.deferred.errback(reason)

    def clientConnectionFailed(self, _, reason):
        """
        When a connection attempt fails, the request cannot be issued.  If no
        result has yet been provided to the result Deferred, provide the
        connection failure reason as an error result.
        """
        if self.waiting:
            self.waiting = 0
            # If the connection attempt failed, there is nothing more to
            # disconnect, so just fire that Deferred now.
            self._disconnectedDeferred.callback(None)
            self.deferred.errback(reason)


class HTTPDownloader(HTTPClientFactory):
    """
    Download to a file.
    """

    protocol = HTTPPageDownloader
    value = None
    _log = Logger()

    def __init__(
        self,
        url,
        fileOrName,
        method=b"GET",
        postdata=None,
        headers=None,
        agent=b"Twisted client",
        supportPartial=False,
        timeout=0,
        cookies=None,
        followRedirect=True,
        redirectLimit=20,
        afterFoundGet=False,
    ):
        self.requestedPartial = 0
        if isinstance(fileOrName, str):
            self.fileName = fileOrName
            self.file = None
            if supportPartial and os.path.exists(self.fileName):
                fileLength = os.path.getsize(self.fileName)
                if fileLength:
                    self.requestedPartial = fileLength
                    if headers is None:
                        headers = {}
                    headers[b"range"] = b"bytes=%d-" % (fileLength,)
        else:
            self.file = fileOrName
        HTTPClientFactory.__init__(
            self,
            url,
            method=method,
            postdata=postdata,
            headers=headers,
            agent=agent,
            timeout=timeout,
            cookies=cookies,
            followRedirect=followRedirect,
            redirectLimit=redirectLimit,
            afterFoundGet=afterFoundGet,
        )

    def gotHeaders(self, headers):
        HTTPClientFactory.gotHeaders(self, headers)
        if self.requestedPartial:
            contentRange = headers.get(b"content-range", None)
            if not contentRange:
                # server doesn't support partial requests, oh well
                self.requestedPartial = 0
                return
            start, end, realLength = http.parseContentRange(contentRange[0])
            if start != self.requestedPartial:
                # server is acting weirdly
                self.requestedPartial = 0

    def openFile(self, partialContent):
        if partialContent:
            file = open(self.fileName, "rb+")
            file.seek(0, 2)
        else:
            file = open(self.fileName, "wb")
        return file

    def pageStart(self, partialContent):
        """Called on page download start.

        @param partialContent: tells us if the download is partial download we
            requested.
        """
        if partialContent and not self.requestedPartial:
            raise ValueError(
                "we shouldn't get partial content response if we didn't "
                "want it!"
            )
        if self.waiting:
            try:
                if not self.file:
                    self.file = self.openFile(partialContent)
            except OSError:
                # raise
                self.deferred.errback(Failure())

    def pagePart(self, data):
        if not self.file:
            return
        try:
            self.file.write(data)
        except OSError:
            # raise
            self.file = None
            self.deferred.errback(Failure())

    def noPage(self, reason):
        """
        Close the storage file and errback the waiting L{Deferred} with the
        given reason.
        """
        if self.waiting:
            self.waiting = 0
            if self.file:
                try:
                    self.file.close()
                except BaseException:
                    self._log.failure("Error closing HTTPDownloader file")
            self.deferred.errback(reason)

    def pageEnd(self):
        self.waiting = 0
        if not self.file:
            return
        try:
            self.file.close()
        except OSError:
            self.deferred.errback(Failure())
            return
        self.deferred.callback(self.value)


def _makeGetterFactory(
    url, factoryFactory, contextFactory=None, *args, **kwargs
):
    """
    Create and connect an HTTP page getting factory.

    Any additional positional or keyword arguments are used when calling
    C{factoryFactory}.

    @param factoryFactory: Factory factory that is called with C{url}, C{args}
        and C{kwargs} to produce the getter

    @param contextFactory: Context factory to use when creating a secure
        connection, defaulting to L{None}

    @return: The factory created by C{factoryFactory}
    """
    uri = URI.fromBytes(_ensureValidURI(url.strip()))
    factory = factoryFactory(url, *args, **kwargs)
    from twisted.internet import reactor

    if uri.scheme == b"https":
        from twisted.internet import ssl

        if contextFactory is None:
            contextFactory = ssl.ClientContextFactory()
        reactor.connectSSL(
            nativeString(uri.host), uri.port, factory, contextFactory
        )
    else:
        reactor.connectTCP(nativeString(uri.host), uri.port, factory)
    return factory


def downloadPage(url, file, contextFactory=None, *args, **kwargs):
    """
    Download a web page to a file.

    @param file: path to file on filesystem, or file-like object.

    See HTTPDownloader to see what extra args can be passed.
    """
    factoryFactory = lambda url, *a, **kw: HTTPDownloader(  # noqa: E731
        url, file, *a, **kw
    )
    kwargs["contextFactory"] = contextFactory
    return _makeGetterFactory(url, factoryFactory, *args, **kwargs).deferred


def _unprefix(url: URL) -> URL:
    prefix = URLs.external.path[:-1]
    assert url.path[: len(prefix)] == prefix, (url.path[len(prefix) :], prefix)
    return url.replace(path=url.path[len(prefix) :])


@attrs(frozen=True, auto_attribs=True, kw_only=True, eq=False)
class ExternalApplication:
    """
    Application with endpoints for cached external resources.
    """

    _log: ClassVar[Logger] = Logger()
    router: ClassVar[Router] = Router()

    config: Configuration

    bootstrapVersionNumber = "3.3.7"
    jqueryVersionNumber = "3.1.0"
    dataTablesVersionNumber = "1.10.12"
    momentVersionNumber = "2.22.2"
    lscacheVersionNumber = "1.0.5"

    bootstrapVersion = f"bootstrap-{bootstrapVersionNumber}-dist"
    jqueryVersion = f"jquery-{jqueryVersionNumber}"
    dataTablesVersion = f"DataTables-{dataTablesVersionNumber}"
    momentVersion = f"moment-{momentVersionNumber}"
    lscacheVersion = f"lscache-{lscacheVersionNumber}"

    bootstrapSourceURL = URL.fromText(
        f"https://github.com/twbs/bootstrap/releases/download/"
        f"v{bootstrapVersionNumber}/{bootstrapVersion}.zip"
    )

    jqueryJSSourceURL = URL.fromText(
        f"https://code.jquery.com/{jqueryVersion}.min.js"
    )

    jqueryMapSourceURL = URL.fromText(
        f"https://code.jquery.com/{jqueryVersion}.min.map"
    )

    # datatables.net has busted TLS
    # dataTablesSourceURL = URL.fromText(
    #     f"https://datatables.net/releases/"
    #     f"DataTables-{dataTablesVersionNumber}.zip"
    # )
    dataTablesSourceURL = URL.fromText(
        f"http://www.wsanchez.net/brr/"
        f"DataTables-{dataTablesVersionNumber}.zip"
    )

    momentJSSourceURL = URL.fromText(
        f"https://cdnjs.cloudflare.com/ajax/libs/moment.js/"
        f"{momentVersionNumber}/moment.min.js"
    )

    lscacheJSSourceURL = URL.fromText(
        f"https://raw.githubusercontent.com/pamelafox/lscache/"
        f"{lscacheVersionNumber}/lscache.min.js"
    )

    @router.route(
        _unprefix(URLs.bootstrapBase), methods=("HEAD", "GET"), branch=True
    )
    @static
    async def bootstrapResource(self, request: IRequest) -> KleinRenderable:
        """
        Endpoint for Bootstrap.
        """
        requestURL = URL.fromText(request.uri.decode("ascii"))

        # Remove URL prefix
        names = requestURL.path[len(URLs.bootstrapBase.path) - 1 :]

        request.setHeader(HeaderName.contentType.value, ContentType.css.value)
        return await self.cachedZippedResource(
            request,
            self.bootstrapSourceURL,
            self.bootstrapVersion,
            self.bootstrapVersion,
            *names,
        )

    @router.route(_unprefix(URLs.jqueryJS), methods=("HEAD", "GET"))
    @static
    async def jqueryJSResource(self, request: IRequest) -> KleinRenderable:
        """
        Endpoint for jQuery.
        """
        request.setHeader(
            HeaderName.contentType.value, ContentType.javascript.value
        )
        return await self.cachedResource(
            request, self.jqueryJSSourceURL, f"{self.jqueryVersion}.min.js"
        )

    @router.route(_unprefix(URLs.jqueryMap), methods=("HEAD", "GET"))
    @static
    async def jqueryMapResource(self, request: IRequest) -> KleinRenderable:
        """
        Endpoint for the jQuery map file.
        """
        request.setHeader(HeaderName.contentType.value, ContentType.json.value)
        return await self.cachedResource(
            request, self.jqueryMapSourceURL, f"{self.jqueryVersion}.min.map"
        )

    @router.route(
        _unprefix(URLs.dataTablesBase), methods=("HEAD", "GET"), branch=True
    )
    @static
    async def dataTablesResource(self, request: IRequest) -> KleinRenderable:
        """
        Endpoint for DataTables.
        """
        requestURL = URL.fromText(request.uri.decode("ascii"))

        # Remove URL prefix
        names = requestURL.path[len(URLs.dataTablesBase.path) - 1 :]

        if names[-1].endswith(".css"):
            contentType = ContentType.css.value
        elif names[-1].endswith(".js"):
            contentType = ContentType.javascript.value
        else:
            return notFoundResponse(request)

        request.setHeader(HeaderName.contentType.value, contentType)

        return await self.cachedZippedResource(
            request,
            self.dataTablesSourceURL,
            self.dataTablesVersion,
            self.dataTablesVersion,
            *names,
        )

    @router.route(_unprefix(URLs.momentJS), methods=("HEAD", "GET"))
    @static
    async def momentJSResource(self, request: IRequest) -> KleinRenderable:
        """
        Endpoint for moment.js.
        """
        request.setHeader(
            HeaderName.contentType.value, ContentType.javascript.value
        )
        return await self.cachedResource(
            request, self.momentJSSourceURL, f"{self.momentVersion}.min.js"
        )

    @router.route(_unprefix(URLs.lscacheJS), methods=("HEAD", "GET"))
    @static
    async def lscacheJSResource(self, request: IRequest) -> KleinRenderable:
        """
        Endpoint for lscache.
        """
        request.setHeader(
            HeaderName.contentType.value, ContentType.javascript.value
        )
        return await self.cachedResource(
            request, self.lscacheJSSourceURL, f"{self.lscacheVersion}.min.js"
        )

    async def cacheFromURL(self, url: URL, name: str) -> Path:
        """
        Download a resource and cache it.
        """
        cacheDir = self.config.cachedResourcesRoot

        destination = cacheDir / name

        if not destination.exists():
            with NamedTemporaryFile(
                dir=str(cacheDir), delete=False, suffix=".tmp"
            ) as tmp:
                path = Path(tmp.name)
                try:
                    await downloadPage(url.asText().encode("utf-8"), tmp)
                except BaseException as e:
                    self._log.critical(
                        "Download failed for {url}: {error}", url=url, error=e
                    )
                    try:
                        path.unlink()
                    except OSError as e:
                        self._log.critical(
                            "Failed to remove temporary file {path}: {error}",
                            path=path,
                            error=e,
                        )
                else:
                    path.rename(destination)

        return destination

    async def cachedResource(
        self, request: IRequest, url: URL, name: str
    ) -> KleinRenderable:
        """
        Retrieve a cached resource.
        """
        path = await self.cacheFromURL(url, name)

        try:
            return path.read_bytes()
        except OSError as e:
            self._log.error(
                "Unable to open file {path}: {error}", path=path, error=e
            )
            return notFoundResponse(request)

    async def cachedZippedResource(
        self,
        request: IRequest,
        url: URL,
        archiveName: str,
        name: str,
        *names: Any,
    ) -> KleinRenderable:
        """
        Retrieve a cached resource from a zip file.
        """
        archivePath = await self.cacheFromURL(url, f"{archiveName}.zip")

        try:
            filePath = ZipArchive(str(archivePath))
        except BadZipfile as e:
            self._log.error(
                "Corrupt zip archive {path}: {error}",
                path=archivePath,
                error=e,
            )
            try:
                archivePath.unlink()
            except OSError as e:
                self._log.critical(
                    "Failed to remove corrupt zip archive {path}: {error}",
                    path=archivePath,
                    error=e,
                )
            return internalErrorResponse(request)
        except OSError as e:
            self._log.critical(
                "Unable to open zip archive {path}: {error}",
                path=archivePath,
                error=e,
            )
            return notFoundResponse(request)

        filePath = filePath.child(name)
        for name in names:
            filePath = filePath.child(name)

        try:
            return filePath.getContent()
        except KeyError:
            self._log.error(
                "File not found in ZIP archive: {filePath.path}",
                filePath=filePath,
                archive=archivePath,
            )
            return notFoundResponse(request)
