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

from collections.abc import Iterable, Iterator, Mapping, Sequence
from contextlib import chdir, contextmanager
from functools import partial
from os import environ, getcwd
from pathlib import Path
from string import ascii_letters, printable
from typing import cast

from hypothesis import assume, given
from hypothesis.strategies import lists, sampled_from, text

from ims.auth import AuthProvider, JSONWebKey
from ims.directory import IMSDirectory
from ims.directory.clubhouse_db import DMSDirectory
from ims.directory.file import FileDirectory
from ims.ext.enum import Enum, Names, auto
from ims.ext.trial import TestCase
from ims.store import IMSDataStore
from ims.store.mysql import DataStore as MySQLDataStore
from ims.store.sqlite import DataStore as SQLiteDataStore

from .._config import (
    ConfigFileParser,
    Configuration,
    ConfigurationError,
    describeFactory,
)


__all__ = ()


emptyConfigFile = Path(__file__).parent / "empty.conf"
sampleConfigFile = Path(__file__).parent / "test.conf"
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


def writeConfig(path: Path, section: str, option: str, value: str) -> None:
    value = value.replace("%", "%%")
    path.write_text(f"[{section}]\n{option} = {value}\n")


class Things(Names):
    """
    Some things.
    """

    cheese = auto()
    butter = auto()
    wheels = auto()
    dogs = auto()
    dirt = auto()


class UtilityTests(TestCase):
    """
    Tests for utilities.
    """

    @staticmethod
    def factory(a: int, b: str, c: bytes) -> bool:
        raise NotImplementedError()

    def test_describeFactory_partial(self) -> None:
        """
        describeFactory() describes a partial object.
        """
        p = partial(self.factory, 1, "some_text", b"some_bytes", q=False)
        self.assertEqual(
            describeFactory(p),
            "factory(1, 'some_text', b'some_bytes', q=False)",
        )

    def test_describeFactory_partial_password(self) -> None:
        """
        describeFactory() redacts passwords from partial objects.
        """
        p = partial(self.factory, 1, password="super secret")  # nosec
        self.assertEqual(
            describeFactory(p), "factory(1, password='(REDACTED)')"
        )

    def test_describeFactory_function(self) -> None:
        """
        describeFactory() describes a function object.
        """
        self.assertEqual(describeFactory(self.factory), "factory(...)")


class ConfigFileParserTests(TestCase):
    """
    Tests for :class:`ConfigFileParser`
    """

    def test_init_path(self) -> None:
        """
        Init path is kept.
        """
        configFilePath = Path(self.mktemp())
        configFilePath.write_text("")

        parser = ConfigFileParser(path=configFilePath)

        self.assertEqual(parser.path, configFilePath)

    def test_init_path_none(self) -> None:
        """
        Init path may be None.
        """
        parser = ConfigFileParser(path=None)

        self.assertIsNone(parser.path)

    def test_init_path_missing(self) -> None:
        """
        Init with missing path is OK.
        """
        configFilePath = Path(self.mktemp())
        assert not configFilePath.exists()

        parser = ConfigFileParser(path=configFilePath)

        self.assertEqual(parser.path, configFilePath)

    @given(
        text(alphabet=ascii_letters, min_size=1),  # variable
        text(alphabet=ascii_letters, min_size=1),  # value
        text(alphabet=ascii_letters, min_size=1),  # section
        text(alphabet=ascii_letters, min_size=1),  # option
        text(),  # default
    )
    def test_valueFromConfig(
        self, variable: str, value: str, section: str, option: str, default: str
    ) -> None:
        """
        ConfigFileParser.valueFromConfig() reads a value from the config file.
        """
        configFilePath = Path(self.mktemp())
        writeConfig(configFilePath, section, option, value)

        parser = ConfigFileParser(path=configFilePath)
        with testingEnvironment({}):
            self.assertEqual(
                parser.valueFromConfig(variable, section, option, default),
                value,
            )

    @given(
        text(alphabet=ascii_letters, min_size=1),  # variable
        text(alphabet=ascii_letters, min_size=1),  # value
        text(alphabet=ascii_letters, min_size=1),  # section
        text(alphabet=ascii_letters, min_size=1),  # option
        text(),  # default
    )
    def test_valueFromConfig_env(
        self, variable: str, value: str, section: str, option: str, default: str
    ) -> None:
        """
        ConfigFileParser.valueFromConfig() reads an environment variable.
        """
        parser = ConfigFileParser(path=None)
        with testingEnvironment({f"IMS_{variable}": value}):
            self.assertEqual(
                parser.valueFromConfig(variable, section, option, default),
                value,
            )

    @given(
        text(alphabet=ascii_letters, min_size=1),  # variable
        text(alphabet=ascii_letters, min_size=1),  # value
        text(alphabet=ascii_letters, min_size=1),  # otherValue
        text(alphabet=ascii_letters, min_size=1),  # section
        text(alphabet=ascii_letters, min_size=1),  # option
        text(),  # default
    )
    def test_valueFromConfig_env_override(
        self,
        variable: str,
        value: str,
        otherValue: str,
        section: str,
        option: str,
        default: str,
    ) -> None:
        """
        ConfigFileParser.valueFromConfig() reads an environment variable even
        if the corresponding value is in the config file.
        """
        assume(value != otherValue)

        configFilePath = Path(self.mktemp())
        writeConfig(configFilePath, section, option, otherValue)

        parser = ConfigFileParser(path=configFilePath)
        with testingEnvironment({f"IMS_{variable}": value}):
            self.assertEqual(
                parser.valueFromConfig(variable, section, option, default),
                value,
            )

    @given(
        text(alphabet=ascii_letters, min_size=1),  # variable
        text(alphabet=ascii_letters, min_size=1),  # value
        text(alphabet=ascii_letters, min_size=1),  # section
        text(alphabet=ascii_letters, min_size=1),  # option
        text(alphabet=ascii_letters, min_size=1),  # otherSection
        text(alphabet=ascii_letters, min_size=1),  # otherOption
        text(),  # default
    )
    def test_valueFromConfig_notFound(
        self,
        variable: str,
        value: str,
        section: str,
        option: str,
        otherSection: str,
        otherOption: str,
        default: str,
    ) -> None:
        """
        ConfigFileParser.valueFromConfig() returns the default value when it
        can't find a value in the environment or config file.
        """
        assume(
            (section.lower(), option.lower())
            != (otherSection.lower(), otherOption.lower())
        )

        configFilePath = Path(self.mktemp())
        writeConfig(configFilePath, section, option, value)

        parser = ConfigFileParser(path=configFilePath)
        with testingEnvironment({}):
            self.assertEqual(
                parser.valueFromConfig(
                    variable, otherSection, otherOption, default
                ),
                default,
            )

    @given(
        text(alphabet=ascii_letters, min_size=1),  # variable
        text(alphabet=ascii_letters, min_size=1),  # section
        text(alphabet=ascii_letters, min_size=1),  # option
        lists(text(alphabet=printable, min_size=1)),  # segments
    )
    def test_pathFromConfig_relative(
        self, variable: str, section: str, option: str, segments: Sequence[str]
    ) -> None:
        """
        ConfigFileParser.pathFromConfig() reads a relative path from the config
        file.
        """
        valuePath = Path(self.mktemp())

        configFilePath = Path(self.mktemp())
        writeConfig(configFilePath, section, option, str(valuePath))

        rootPath = Path.cwd()  # self.mktemp returns a path relative to cwd

        parser = ConfigFileParser(path=configFilePath)
        with testingEnvironment({}):
            self.assertEqual(
                parser.pathFromConfig(
                    variable, section, option, rootPath, segments
                ),
                valuePath.resolve(),
            )

    @given(
        text(alphabet=ascii_letters, min_size=1),  # variable
        text(alphabet=ascii_letters, min_size=1),  # section
        text(alphabet=ascii_letters, min_size=1),  # option
        lists(text(alphabet=printable, min_size=1)),  # segments
    )
    def test_pathFromConfig_absolute(
        self, variable: str, section: str, option: str, segments: Sequence[str]
    ) -> None:
        """
        ConfigFileParser.pathFromConfig() reads an absolute path from the
        config file.
        """
        valuePath = Path(self.mktemp()).resolve()

        configFilePath = Path(self.mktemp())
        writeConfig(configFilePath, section, option, str(valuePath))

        rootPath = Path(self.mktemp())

        parser = ConfigFileParser(path=configFilePath)
        with testingEnvironment({}):
            self.assertEqual(
                parser.pathFromConfig(
                    variable, section, option, rootPath, segments
                ),
                valuePath,
            )

    @given(
        text(alphabet=ascii_letters, min_size=1),  # variable
        text(alphabet=ascii_letters, min_size=1),  # section
        text(alphabet=ascii_letters, min_size=1),  # option
        text(alphabet=ascii_letters, min_size=1),  # otherSection
        text(alphabet=ascii_letters, min_size=1),  # otherOption
        lists(text(alphabet=printable, min_size=1)),  # segments
    )
    def test_pathFromConfig_notFound(
        self,
        variable: str,
        section: str,
        option: str,
        otherSection: str,
        otherOption: str,
        segments: Sequence[str],
    ) -> None:
        """
        ConfigFileParser.pathFromConfig() reads an absolute path from the
        config file.
        """
        assume(
            (section.lower(), option.lower())
            != (otherSection.lower(), otherOption.lower())
        )

        valuePath = Path(self.mktemp())

        configFilePath = Path(self.mktemp())
        writeConfig(configFilePath, section, option, str(valuePath))

        rootPath = Path(self.mktemp())

        parser = ConfigFileParser(path=configFilePath)
        with testingEnvironment({}):
            self.assertEqual(
                parser.pathFromConfig(
                    variable, otherSection, otherOption, rootPath, segments
                ),
                rootPath.resolve().joinpath(*segments),
            )

    @given(
        text(alphabet=ascii_letters, min_size=1),  # variable
        sampled_from(Things),  # value
        text(alphabet=ascii_letters, min_size=1),  # section
        text(alphabet=ascii_letters, min_size=1),  # option
        sampled_from(Things),  # default
    )
    def test_enumFromConfig(
        self,
        variable: str,
        value: Enum,
        section: str,
        option: str,
        default: Enum,
    ) -> None:
        """
        ConfigFileParser.enumFromConfig() reads a enumerated value from the
        config file.
        """
        configFilePath = Path(self.mktemp())
        writeConfig(configFilePath, section, option, value.name)

        parser = ConfigFileParser(path=configFilePath)
        with testingEnvironment({}):
            self.assertEqual(
                parser.enumFromConfig(variable, section, option, default),
                value,
            )

    @given(
        text(alphabet=ascii_letters, min_size=1),  # variable
        sampled_from(Things),  # value
        text(alphabet=ascii_letters, min_size=1),  # section
        text(alphabet=ascii_letters, min_size=1),  # option
        text(alphabet=ascii_letters, min_size=1),  # otherSection
        text(alphabet=ascii_letters, min_size=1),  # otherOption
        sampled_from(Things),  # default
    )
    def test_enumFromConfig_notFound(
        self,
        variable: str,
        value: Enum,
        section: str,
        option: str,
        otherSection: str,
        otherOption: str,
        default: Enum,
    ) -> None:
        """
        ConfigFileParser.enumFromConfig() returns the default value when it
        can't find a value in the environment or config file.
        """
        assume(
            (section.lower(), option.lower())
            != (otherSection.lower(), otherOption.lower())
        )

        configFilePath = Path(self.mktemp())
        writeConfig(configFilePath, section, option, value.name)

        parser = ConfigFileParser(path=configFilePath)
        with testingEnvironment({}):
            self.assertEqual(
                parser.enumFromConfig(
                    variable, otherSection, otherOption, default
                ),
                default,
            )

    @given(
        text(alphabet=ascii_letters, min_size=1),  # variable
        sampled_from(Things),  # value
        text(alphabet=ascii_letters, min_size=1),  # otherValue
        text(alphabet=ascii_letters, min_size=1),  # section
        text(alphabet=ascii_letters, min_size=1),  # option
        sampled_from(Things),  # default
    )
    def test_enumFromConfig_unknown(
        self,
        variable: str,
        value: Enum,
        otherValue: str,
        section: str,
        option: str,
        default: Enum,
    ) -> None:
        """
        ConfigFileParser.enumFromConfig() reads a enumerated value from the
        config file.
        """
        assume(otherValue not in [t.name for t in Things])

        configFilePath = Path(self.mktemp())
        writeConfig(configFilePath, section, option, otherValue)

        parser = ConfigFileParser(path=configFilePath)
        with testingEnvironment({}):
            e = self.assertRaises(
                ConfigurationError,
                parser.enumFromConfig,
                variable,
                section,
                option,
                default,
            )
            self.assertStartsWith(str(e), "Invalid option ")


class ConfigurationTests(TestCase):
    """
    Tests for :class:`Configuration`
    """

    def _test_fromConfigFile_defaults(
        self, configFile: Path | None, serverRoot: Path
    ) -> None:
        config = Configuration.fromConfigFile(configFile)

        configRoot = serverRoot / "conf"
        dataRoot = serverRoot / "data"
        cached = dataRoot / "cache"

        self.assertEqual(config.serverRoot, serverRoot)
        self.assertEqual(config.configRoot, configRoot)
        self.assertEqual(config.dataRoot, dataRoot)
        self.assertEqual(config.cachedResourcesRoot, cached)

        directory = cast(FileDirectory, config.directory)

        self.assertIsInstance(directory, FileDirectory)
        self.assertEqual(
            directory.path.resolve(),
            (config.configRoot / "directory.yaml").resolve(),
        )

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
        dataRoot = serverRoot / "infos"
        cached = dataRoot / "stuff"

        self.assertEqual(config.serverRoot, serverRoot)
        self.assertEqual(config.configRoot, configRoot)
        self.assertEqual(config.dataRoot, dataRoot)
        self.assertEqual(config.cachedResourcesRoot, cached)

    def test_fromConfigFile_environment_value(self) -> None:
        """
        Text value from environment.
        """
        hostName = "xyzzy"

        with testingEnvironment(dict(IMS_HOSTNAME=hostName)):
            config = Configuration.fromConfigFile(None)

        self.assertEqual(config.hostName, hostName)

    def test_fromConfigFile_environment_path_absolute(self) -> None:
        """
        Absolute path from environment.
        """
        path = Path(self.mktemp()).resolve()

        with testingEnvironment(dict(IMS_SERVER_ROOT=str(path))):
            config = Configuration.fromConfigFile(None)

        self.assertEqual(config.serverRoot, path)

    def test_fromConfigFile_createDirectories(self) -> None:
        """
        Server root and friends are created if they don't exist.
        """
        tmp = Path(self.mktemp())
        path = tmp / "ims_server_root"

        tmp.mkdir()

        with testingEnvironment(dict(IMS_SERVER_ROOT=str(path))):
            config = Configuration.fromConfigFile(None)

        self.assertTrue(config.serverRoot.is_dir())
        self.assertTrue(config.dataRoot.is_dir())
        self.assertTrue(config.cachedResourcesRoot.is_dir())
        self.assertTrue(config.serverRoot.is_dir())

    def test_fromConfigFile_admins(self) -> None:
        """
        Admins from list
        """
        empty: set[str] = set()
        data: Iterable[tuple[str, set[str]]] = (
            ("", empty),
            (",,", empty),
            ("a,b,c", {"a", "b", "c"}),
            ("c,,c,a", {"a", "c"}),
        )

        for value, result in data:
            with testingEnvironment(dict(IMS_ADMINS=value)):
                config = Configuration.fromConfigFile(None)

            self.assertEqual(config.imsAdmins, result)

    def test_fromConfigFile_requireActive(self) -> None:
        """
        RequireActive boolean values.
        """

        def test(value: str) -> bool:
            with testingEnvironment(dict(IMS_REQUIRE_ACTIVE=value)):
                config = Configuration.fromConfigFile(None)
            return config.requireActive

        for value in ("false", "False", "FALSE", "no", "No", "NO", "0"):
            self.assertFalse(test(value))

        for value in ("true", "True", "TRUE", "yes", "Yes", "YES", "1"):
            self.assertTrue(test(value))

    @given(text(alphabet=printable, min_size=1))
    def test_fromConfigFile_jwtSecret(self, secret: str) -> None:
        """
        JWTSecret value creates a corresponding key.
        """

        def test(secret: str) -> JSONWebKey:
            with testingEnvironment(dict(IMS_JWT_SECRET=secret)):
                config = Configuration.fromConfigFile(None)
            return config.jsonWebKey

        self.assertEqual(test(secret), JSONWebKey.fromSecret(secret))

    def test_fromConfigFile_jwtSecret_empty(self) -> None:
        """
        JWTSecret with no value creates a random key.
        """
        with testingEnvironment({}):
            config = Configuration.fromConfigFile(None)

        self.assertIsInstance(config.jsonWebKey, JSONWebKey)

    def test_store(self) -> None:
        with testingEnvironment({}):
            config = Configuration.fromConfigFile(None)

        self.assertIsNone(config._state.store)
        self.assertIsInstance(config.store, IMSDataStore)
        self.assertIsNotNone(config._state.store)
        self.assertIsInstance(config.store, IMSDataStore)

    def test_store_sqlite(self) -> None:
        path = Path(self.mktemp()).resolve() / "ims.sqlite"

        with testingEnvironment(
            dict(IMS_DATA_STORE="SQLite", IMS_DB_PATH=str(path))
        ):
            config = Configuration.fromConfigFile(None)

        self.assertIsInstance(config.store, SQLiteDataStore)
        self.assertEqual(cast(SQLiteDataStore, config.store).dbPath, path)

    def test_store_mysql(self) -> None:
        hostName = "db_host"
        hostPort = 72984
        database = "ranger_ims"
        userName = "ims_user"
        password = "hoorj"  # nosec

        with testingEnvironment(
            dict(
                IMS_DATA_STORE="MySQL",
                IMS_DB_HOST_NAME=hostName,
                IMS_DB_HOST_PORT=str(hostPort),
                IMS_DB_DATABASE=database,
                IMS_DB_USER_NAME=userName,
                IMS_DB_PASSWORD=password,
            )
        ):
            config = Configuration.fromConfigFile(None)

        store = cast(MySQLDataStore, config.store)

        self.assertIsInstance(store, MySQLDataStore)
        self.assertEqual(store.hostName, hostName)
        self.assertEqual(store.hostPort, hostPort)
        self.assertEqual(store.database, database)
        self.assertEqual(store.username, userName)
        self.assertEqual(store.password, password)

    def test_store_unknown(self) -> None:
        storeName = "XYZZY"
        with testingEnvironment(dict(IMS_DATA_STORE=storeName)):
            e = self.assertRaises(
                ConfigurationError, Configuration.fromConfigFile, None
            )
            self.assertEqual(str(e), f"Unknown data store: {storeName!r}")

    def test_directory(self) -> None:
        with testingEnvironment({}):
            config = Configuration.fromConfigFile(None)

        self.assertIsInstance(config.directory, IMSDirectory)

    def test_directory_file(self) -> None:
        path = Path(self.mktemp()).resolve() / "directory.yaml"

        with testingEnvironment(
            dict(IMS_DIRECTORY="File", IMS_DIRECTORY_FILE=str(path))
        ):
            config = Configuration.fromConfigFile(None)

        directory = cast(FileDirectory, config.directory)

        self.assertIsInstance(directory, FileDirectory)
        self.assertEqual(directory.path, path)

    def test_directory_clubhouseDB(self) -> None:
        hostName = "clubhouse_host"
        database = "rangers"
        userName = "rangers"
        password = "hoorj"  # nosec

        with testingEnvironment(
            dict(
                IMS_DIRECTORY="ClubhouseDB",
                IMS_DMS_HOSTNAME=hostName,
                IMS_DMS_DATABASE=database,
                IMS_DMS_USERNAME=userName,
                IMS_DMS_PASSWORD=password,
            ),
        ):
            config = Configuration.fromConfigFile(None)

        directory = cast(DMSDirectory, config.directory)

        self.assertIsInstance(directory, DMSDirectory)
        self.assertEqual(directory._dms.host, hostName)
        self.assertEqual(directory._dms.database, database)
        self.assertEqual(directory._dms.username, userName)
        self.assertEqual(directory._dms.password, password)

    def test_directory_unknown(self) -> None:
        storeName = "XYZZY"
        with testingEnvironment(dict(IMS_DIRECTORY=storeName)):
            e = self.assertRaises(
                ConfigurationError, Configuration.fromConfigFile, None
            )
            self.assertEqual(str(e), f"Unknown directory: {storeName!r}")

    def test_authProvider(self) -> None:
        with testingEnvironment({}):
            config = Configuration.fromConfigFile(None)

        self.assertIsNone(config._state.authProvider)
        self.assertIsInstance(config.authProvider, AuthProvider)
        self.assertIsNotNone(config._state.authProvider)
        self.assertIsInstance(config.authProvider, AuthProvider)

    def test_str(self) -> None:
        with testingEnvironment({}):
            config = Configuration.fromConfigFile(None)

        self.maxDiff = None
        self.assertEqual(
            str(config),
            f"Configuration file: None\n"
            f"\n"
            f"Core.Host: {config.hostName}\n"
            f"Core.Port: {config.port}\n"
            f"\n"
            f"Core.ServerRoot: {config.serverRoot}\n"
            f"Core.ConfigRoot: {config.configRoot}\n"
            f"Core.DataRoot: {config.dataRoot}\n"
            f"Core.CachedResources: {config.cachedResourcesRoot}\n"
            f"Core.LogLevel: {config.logLevelName}\n"
            f"Core.LogFile: {config.logFilePath}\n"
            f"Core.LogFormat: {config.logFormat}\n"
            f"\n"
            f"DataStore: {describeFactory(config._storeFactory)}\n"
            f"Directory: {config.directory}\n",
        )

    def test_replace(self) -> None:
        hostName = "xyzzy"

        with testingEnvironment({}):
            config = Configuration.fromConfigFile(None)

        config = config.replace(hostName=hostName)

        self.assertEqual(config.hostName, hostName)
