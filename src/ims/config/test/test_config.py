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
from typing import Iterable, Iterator, Mapping, Optional, Set, Tuple

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

        self.assertEqual(config.ServerRoot, serverRoot)
        self.assertEqual(config.ConfigRoot, configRoot)
        self.assertEqual(config.DataRoot, dataRoot)
        self.assertEqual(config.CachedResourcesRoot, cached)

        self.assertEqual(config.DMSHost, "")
        self.assertEqual(config.DMSDatabase, "")
        self.assertEqual(config.DMSUsername, "")
        self.assertEqual(config.DMSPassword, "")


    def test_fromConfigFile_none(self) -> None:
        """
        No config file provided.
        """
        self._test_fromConfigFile_defaults(None, Path(getcwd()))


    def test_fromConfigFile_empty(self) -> None:
        """
        Empty config file provided.
        """
        self._test_fromConfigFile_defaults(
            emptyConfigFile, Path(__file__).parent.parent
        )


    def test_fromConfigFile_missing(self) -> None:
        """
        Non-existent config file provided.
        """
        self._test_fromConfigFile_defaults(
            missingConfigFile, Path(__file__).parent.parent
        )


    def test_fromConfigFile_sampleConfig(self) -> None:
        """
        Config file provided with some config values.
        """
        config = Configuration.fromConfigFile(sampleConfigFile)

        serverRoot = sampleConfigFile.parent.parent
        configRoot = serverRoot / "config"
        dataRoot   = serverRoot / "infos"
        cached     = dataRoot / "stuff"

        self.assertEqual(config.ServerRoot, serverRoot)
        self.assertEqual(config.ConfigRoot, configRoot)
        self.assertEqual(config.DataRoot, dataRoot)
        self.assertEqual(config.CachedResourcesRoot, cached)

        self.assertEqual(config.DMSHost, "dms.rangers.example.com")
        self.assertEqual(config.DMSDatabase, "rangers")
        self.assertEqual(config.DMSUsername, "ims")
        self.assertEqual(
            config.DMSPassword, "9F29BB2B-E775-489C-9C20-9FE3EFEE1F22"
        )


    def test_fromConfigFile_environment_value(self) -> None:
        """
        Text value from environment.
        """
        hostName = "xyzzy"

        with testingEnvironment(dict(IMS_HOSTNAME=hostName)):
            config = Configuration.fromConfigFile(None)

        self.assertEqual(config.HostName, hostName)


    def test_fromConfigFile_environment_path_relative(self) -> None:
        """
        Relative path from environment.
        """
        textPath = self.mktemp()

        assert not textPath.startswith("/")

        with testingEnvironment(dict(IMS_SERVER_ROOT=textPath)):
            config = Configuration.fromConfigFile(None)

        self.assertTrue(Path(textPath).samefile(config.ServerRoot))


    def test_fromConfigFile_environment_path_absolute(self) -> None:
        """
        Absolute path from environment.
        """
        path = Path(self.mktemp()).resolve()

        with testingEnvironment(dict(IMS_SERVER_ROOT=str(path))):
            config = Configuration.fromConfigFile(None)

        self.assertEqual(config.ServerRoot, path)


    def test_fromConfigFile_createDirectories(self) -> None:
        """
        Server root and friends are created if they don't exist.
        """
        tmp = Path(self.mktemp())
        path = tmp / "ims_server_root"

        tmp.mkdir()

        with testingEnvironment(dict(IMS_SERVER_ROOT=str(path))):
            config = Configuration.fromConfigFile(None)

        self.assertTrue(config.ServerRoot.is_dir())
        self.assertTrue(config.ConfigRoot.is_dir())
        self.assertTrue(config.DataRoot.is_dir())
        self.assertTrue(config.CachedResourcesRoot.is_dir())
        self.assertTrue(config.ServerRoot.is_dir())


    def test_fromConfigFile_admins(self) -> None:
        """
        Admins from list
        """
        empty: Set[str] = set()
        data: Iterable[Tuple[str, Set[str]]] = (
            ("", empty),
            (",,", empty),
            ("a,b,c", {"a", "b", "c"}),
            ("c,,c,a", {"a", "c"}),
        )

        for value, result in data:
            with testingEnvironment(dict(IMS_ADMINS=value)):
                config = Configuration.fromConfigFile(None)

            self.assertEqual(config.IMSAdmins, result)


    def test_fromConfigFile_requireActive(self) -> None:
        """
        RequireActive boolean values.
        """
        def test(value: str) -> bool:
            with testingEnvironment(dict(IMS_REQUIRE_ACTIVE=value)):
                config = Configuration.fromConfigFile(None)
            return config.RequireActive

        for value in ("false", "False", "FALSE", "no", "No", "NO", "0"):
            self.assertFalse(test(value))

        for value in ("true", "True", "TRUE", "yes", "Yes", "YES", "1"):
            self.assertTrue(test(value))
