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
Incident Management System web service.
"""

from attr import Factory, attrib, attrs
from attr.validators import instance_of

from twisted.logger import ILogObserver, Logger, globalLogPublisher
from twisted.web.iweb import IRequest

from ims.application._auth import AuthApplication, AuthProvider
from ims.application._eventsource import DataStoreEventSourceLogObserver
from ims.application._klein import router
from ims.application._urls import URLs
from ims.dms import DutyManagementSystem
from ims.ext.klein import KleinRenderable
from ims.store import IMSDataStore

from .config import Configuration
from .external import ExternalMixIn
from .json import JSONMixIn
from .web import WebMixIn


__all__ = (
    "WebService",
)



@attrs(frozen=True)
class WebService(JSONMixIn, WebMixIn, ExternalMixIn):
    """
    Incident Management System web service.
    """

    log = _log = Logger()
    router = router


    config: Configuration = attrib(validator=instance_of(Configuration))

    storeObserver: ILogObserver = attrib(
        default=Factory(DataStoreEventSourceLogObserver), init=False
    )

    auth: AuthProvider = attrib(
        default=Factory(
            lambda self: AuthProvider(config=self.config), takes_self=True
        ),
        init=False,
    )
    _authApplication: AuthApplication = attrib(
        default=Factory(
            lambda self: AuthApplication(auth=self.auth, config=self.config),
            takes_self=True,
        ),
        init=False,
    )


    @property
    def storage(self) -> IMSDataStore:
        return self.config.storage


    @property
    def dms(self) -> DutyManagementSystem:
        return self.config.dms


    def __attrs_post_init__(self) -> None:
        globalLogPublisher.addObserver(self.storeObserver)


    def __del__(self) -> None:
        globalLogPublisher.removeObserver(self.storeObserver)


    #
    # Auth
    #

    @router.route(URLs.auth, branch=True)
    def authApplication(self, request: IRequest) -> KleinRenderable:
        """
        Auth resource.
        """
        return self._authApplication.router.resource()
