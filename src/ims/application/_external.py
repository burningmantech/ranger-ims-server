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

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, ClassVar
from zipfile import BadZipfile

from attr import attrs

from hyperlink import URL

from twisted.logger import Logger
from twisted.python.zippath import ZipArchive
from twisted.web.client import downloadPage
from twisted.web.iweb import IRequest

from ims.config import Configuration, URLs
from ims.ext.klein import ContentType, HeaderName, KleinRenderable, static

from ._klein import Router, internalErrorResponse, notFoundResponse


__all__ = (
    "ExternalApplication",
)


def _unprefix(url: URL) -> URL:
    prefix = URLs.external.path[:-1]
    assert url.path[:len(prefix)] == prefix, (url.path[len(prefix):], prefix)
    return url.replace(path=url.path[len(prefix):])



@attrs(frozen=True, auto_attribs=True, kw_only=True, cmp=False)
class ExternalApplication(object):
    """
    Application with endpoints for cached external resources.
    """

    _log: ClassVar = Logger()
    router: ClassVar = Router()

    config: Configuration

    bootstrapVersionNumber  = "3.3.7"
    jqueryVersionNumber     = "3.1.0"
    dataTablesVersionNumber = "1.10.12"
    momentVersionNumber     = "2.22.2"
    lscacheVersionNumber    = "1.0.5"

    bootstrapVersion  = f"bootstrap-{bootstrapVersionNumber}-dist"
    jqueryVersion     = f"jquery-{jqueryVersionNumber}"
    dataTablesVersion = f"DataTables-{dataTablesVersionNumber}"
    momentVersion     = f"moment-{momentVersionNumber}"
    lscacheVersion    = f"lscache-{lscacheVersionNumber}"

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

    dataTablesSourceURL = URL.fromText(
        f"https://datatables.net/releases/"
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
        cacheDir = self.config.CachedResourcesPath

        destination = cacheDir / name

        if not destination.exists():
            with NamedTemporaryFile(
                dir=str(cacheDir), delete=False, suffix=".tmp"
            ) as tmp:
                path = Path(tmp.name)
                try:
                    await downloadPage(
                        url.asText().encode("utf-8"), tmp
                    )
                except BaseException as e:
                    self._log.failure(
                        "Download failed for {url}: {error}", url=url, error=e
                    )
                    try:
                        path.unlink()
                    except (OSError, IOError) as e:
                        self._log.critical(
                            "Failed to remove temporary file {path}: {error}",
                            path=path, error=e
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
        except (OSError, IOError) as e:
            self._log.error(
                "Unable to open file {path}: {error}", path=path, error=e
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
            url, f"{archiveName}.zip"
        )

        try:
            filePath = ZipArchive(str(archivePath))
        except BadZipfile as e:
            self._log.error(
                "Corrupt zip archive {path}: {error}",
                path=archivePath, error=e,
            )
            try:
                archivePath.unlink()
            except (OSError, IOError) as e:
                self._log.critical(
                    "Failed to remove corrupt zip archive {path}: {error}",
                    path=archivePath, error=e,
                )
            return internalErrorResponse(request)
        except (OSError, IOError) as e:
            self._log.critical(
                "Unable to open zip archive {path}: {error}",
                path=archivePath, error=e,
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
                filePath=filePath, archive=archivePath,
            )
            return notFoundResponse(request)
