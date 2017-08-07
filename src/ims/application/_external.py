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

from typing import Any
from zipfile import BadZipfile

from attr import attrib, attrs
from attr.validators import instance_of

from hyperlink import URL

from twisted.logger import Logger
from twisted.python.filepath import FilePath
from twisted.python.zippath import ZipArchive
from twisted.web.client import downloadPage
from twisted.web.iweb import IRequest

from ims.ext.klein import ContentType, HeaderName, KleinRenderable, static

from ._config import Configuration
from ._klein import Router, notFoundResponse
from ._urls import URLs
from .auth._provider import AuthProvider


__all__ = (
    "ExternalApplication",
)


def _unprefix(url: URL) -> URL:
    prefix = URLs.external.path[:-1]
    assert url.path[:len(prefix)] == prefix, (url.path[len(prefix):], prefix)
    return url.replace(path=url.path[len(prefix):])



@attrs(frozen=True)
class ExternalApplication(object):
    """
    Application with endpoints for cached external resources.
    """

    _log = Logger()
    router = Router()

    auth: AuthProvider = attrib(validator=instance_of(AuthProvider))
    config: Configuration = attrib(validator=instance_of(Configuration))

    bootstrapVersionNumber  = "3.3.7"
    jqueryVersionNumber     = "3.1.0"
    dataTablesVersionNumber = "1.10.12"
    momentVersionNumber     = "2.14.1"
    lscacheVersionNumber    = "1.0.5"

    bootstrapVersion  = "bootstrap-{}-dist".format(bootstrapVersionNumber)
    jqueryVersion     = "jquery-{}".format(jqueryVersionNumber)
    dataTablesVersion = "DataTables-{}".format(dataTablesVersionNumber)
    momentVersion     = "moment-{}".format(momentVersionNumber)
    lscacheVersion    = "lscache-{}".format(lscacheVersionNumber)

    bootstrapSourceURL = URL.fromText(
        "https://github.com/twbs/bootstrap/releases/download/v{n}/{v}.zip"
        .format(n=bootstrapVersionNumber, v=bootstrapVersion)
    )

    jqueryJSSourceURL = URL.fromText(
        "https://code.jquery.com/{v}.min.js"
        .format(n=jqueryVersionNumber, v=jqueryVersion)
    )

    jqueryMapSourceURL = URL.fromText(
        "https://code.jquery.com/{v}.min.map"
        .format(n=jqueryVersionNumber, v=jqueryVersion)
    )

    dataTablesSourceURL = URL.fromText(
        "https://datatables.net/releases/DataTables-{n}.zip"
        .format(n=dataTablesVersionNumber, v=dataTablesVersion)
    )

    momentJSSourceURL = URL.fromText(
        "https://cdnjs.cloudflare.com/ajax/libs/moment.js/{n}/moment.min.js"
        .format(n=momentVersionNumber)
    )

    lscacheJSSourceURL = URL.fromText(
        "https://raw.githubusercontent.com/pamelafox/lscache/{n}/"
        "lscache.min.js"
        .format(n=lscacheVersionNumber)
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
        names = requestURL.path[len(URLs.bootstrapBase.path) - 1:]

        request.setHeader(HeaderName.contentType.value, ContentType.css.value)
        return await self.cachedZippedResource(
            request, self.bootstrapSourceURL, self.bootstrapVersion,
            self.bootstrapVersion, *names
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
            request, self.jqueryJSSourceURL,
            "{}.min.js".format(self.jqueryVersion),
        )


    @router.route(_unprefix(URLs.jqueryMap), methods=("HEAD", "GET"))
    @static
    async def jqueryMapResource(self, request: IRequest) -> KleinRenderable:
        """
        Endpoint for the jQuery map file.
        """
        request.setHeader(HeaderName.contentType.value, ContentType.json.value)
        return await self.cachedResource(
            request, self.jqueryMapSourceURL,
            "{}.min.map".format(self.jqueryVersion),
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
        names = requestURL.path[len(URLs.dataTablesBase.path) - 1:]

        request.setHeader(HeaderName.contentType.value, ContentType.css.value)
        return await self.cachedZippedResource(
            request, self.dataTablesSourceURL, self.dataTablesVersion,
            self.dataTablesVersion, *names
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
            request, self.momentJSSourceURL,
            "{}.min.js".format(self.momentVersion),
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
            request, self.lscacheJSSourceURL,
            "{}.min.js".format(self.lscacheVersion),
        )


    async def cacheFromURL(self, url: URL, name: str) -> FilePath:
        """
        Download a resource and cache it.
        """
        cacheDir = self.config.CachedResources

        if not cacheDir.isdir():
            cacheDir.createDirectory()

        destination = cacheDir.child(name)

        if not destination.exists():
            tmp = destination.temporarySibling(extension=".tmp")
            try:
                await downloadPage(
                    url.asText().encode("utf-8"), tmp.open("w")
                )
            except BaseException:
                self._log.failure("Download failed for {url}", url=url)
                try:
                    tmp.remove()
                except (OSError, IOError):
                    pass
            else:
                tmp.moveTo(destination)

        return destination


    async def cachedResource(
        self, request: IRequest, url: URL, name: str
    ) -> KleinRenderable:
        """
        Retrieve a cached resource.
        """
        filePath = await self.cacheFromURL(url, name)

        try:
            return filePath.getContent()
        except (OSError, IOError) as e:
            self._log.error(
                "Unable to open file {filePath.path}: {error}",
                filePath=filePath, error=e,
            )
            return notFoundResponse(request)


    async def cachedZippedResource(
        self, request: IRequest, url: URL, archiveName: str, name: str,
        *names: Any,
    ) -> KleinRenderable:
        """
        Retrieve a cached resource from a zip file.
        """
        archivePath = await self.cacheFromURL(
            url, "{0}.zip".format(archiveName)
        )

        try:
            filePath = ZipArchive(archivePath.path)
        except BadZipfile as e:
            self._log.error(
                "Corrupt zip archive {archive.path}: {error}",
                archive=archivePath, error=e,
            )
            try:
                archivePath.remove()
            except (OSError, IOError):
                pass
            return notFoundResponse(request)
        except (OSError, IOError) as e:
            self._log.error(
                "Unable to open zip archive {archive.path}: {error}",
                archive=archivePath, error=e,
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
