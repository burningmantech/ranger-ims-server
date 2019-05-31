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
Tests for L{ims.config._config}.
"""

from contextlib import contextmanager
from os import environ, getcwd
from pathlib import Path
from typing import Iterator, Mapping, Optional

from ims.ext.trial import TestCase

from .._config import Configuration


__all__ = ()


emptyConfigFile   = Path(__file__).parent / "empty.conf"
sampleConfigFile  = Path(__file__).parent / "test.conf"
missingConfigFile = Path(__file__).parent / "missing.conf"


@contextmanager
def testingEnvironment(environment: Mapping[str, str]) -> Iterator[None]:
    savedEnvironment = environ.copy()

    environ.clear()
    environ.update(environment)

    try:
        yield

    finally:
        environ.clear()
        environ.update(savedEnvironment)



class ConfigurationTests(TestCase):
    """
    Tests for :class:`Configuration`
    """

    def _test_fromConfigFile_defaults(
        self, configFile: Optional[Path], serverRoot: Path
    ) -> None:
        config = Configuration.fromConfigFile(configFile)

        configRoot = serverRoot / "conf"
        dataRoot   = serverRoot / "data"
        cached     = dataRoot / "cache"

        self.assertEquals(config.ServerRoot, serverRoot)
        self.assertEquals(config.ConfigRoot, configRoot)
        self.assertEquals(config.DataRoot, dataRoot)
        self.assertEquals(config.CachedResourcesRoot, cached)

        self.assertEquals(config.DMSHost, "")
        self.assertEquals(config.DMSDatabase, "")
        self.assertEquals(config.DMSUsername, "")
        self.assertEquals(config.DMSPassword, "")


    def test_fromConfigFile_none(self) -> None:
        self._test_fromConfigFile_defaults(None, Path(getcwd()))


    def test_fromConfigFile_empty(self) -> None:
        self._test_fromConfigFile_defaults(
            emptyConfigFile, Path(__file__).parent.parent
        )


    def test_fromConfigFile_missing(self) -> None:
        self._test_fromConfigFile_defaults(
            missingConfigFile, Path(__file__).parent.parent
        )


    def test_fromConfigFile_sampleConfig(self) -> None:
        config = Configuration.fromConfigFile(sampleConfigFile)

        serverRoot = sampleConfigFile.parent.parent
        configRoot = serverRoot / "conf"
        dataRoot   = serverRoot / "data"
        cached     = dataRoot / "cache"

        self.assertEquals(config.ServerRoot, serverRoot)
        self.assertEquals(config.ConfigRoot, configRoot)
        self.assertEquals(config.DataRoot, dataRoot)
        self.assertEquals(config.CachedResourcesRoot, cached)

        # self.assertEquals(config.DMSHost, "dms.rangers.example.com")
        self.assertEquals(config.DMSDatabase, "rangers")
        self.assertEquals(config.DMSUsername, "ims")
        self.assertEquals(
            config.DMSPassword, "9F29BB2B-E775-489C-9C20-9FE3EFEE1F22"
        )


    def test_fromConfigFile_environment_value(self) -> None:
        hostName = "xyzzy"

        with testingEnvironment(dict(IMS_HOSTNAME=hostName)):
            config = Configuration.fromConfigFile(None)

        self.assertEquals(config.HostName, hostName)


    def test_fromConfigFile_environment_path_relative(self) -> None:
        textPath = self.mktemp()

        assert not textPath.startswith("/")

        with testingEnvironment(dict(IMS_SERVER_ROOT=textPath)):
            config = Configuration.fromConfigFile(None)

        self.assertTrue(Path(textPath).samefile(config.ServerRoot))


    def test_fromConfigFile_environment_path_absolute(self) -> None:
        path = Path(self.mktemp()).resolve()

        with testingEnvironment(dict(IMS_SERVER_ROOT=str(path))):
            config = Configuration.fromConfigFile(None)

        self.assertEqual(config.ServerRoot, path)


    def test_fromConfigFile_requireActive(self) -> None:
        def test(value: str) -> bool:
            with testingEnvironment(dict(IMS_REQUIRE_ACTIVE=value)):
                config = Configuration.fromConfigFile(None)
            return config.RequireActive

        for value in ("false", "False", "FALSE", "no", "No", "NO", "0"):
            self.assertFalse(test(value))

        for value in ("true", "True", "TRUE", "yes", "Yes", "YES", "1"):
            self.assertTrue(test(value))
