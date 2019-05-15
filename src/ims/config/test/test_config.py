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

from pathlib import Path

from ims.ext.trial import TestCase

from .._config import Configuration


__all__ = ()


emptyConfigFile  = Path(__file__).parent / "empty.conf"
sampleConfigFile = Path(__file__).parent / "test.conf"



class ConfigurationTests(TestCase):
    """
    Tests for :class:`Configuration`
    """

    def test_defaults(self) -> None:
        """
        Check defaults.
        """
        assert emptyConfigFile.is_file(), emptyConfigFile

        config = Configuration.fromConfigFile(emptyConfigFile)

        serverRoot = Path(__file__).parent.parent
        configRoot = serverRoot / "conf"
        dataRoot   = serverRoot / "data"
        cached     = dataRoot / "cache"

        self.assertEquals(config.ServerRoot, serverRoot)
        self.assertEquals(config.ConfigRoot, configRoot)
        self.assertEquals(config.DataRoot, dataRoot)
        self.assertEquals(config.CachedResourcesPath, cached)

        self.assertEquals(config.DMSHost, None)
        self.assertEquals(config.DMSDatabase, None)
        self.assertEquals(config.DMSUsername, None)
        self.assertEquals(config.DMSPassword, None)


    def test_sampleConfig(self) -> None:
        """
        Check sample config.
        """
        assert sampleConfigFile.is_file(), sampleConfigFile

        config = Configuration.fromConfigFile(sampleConfigFile)

        serverRoot = sampleConfigFile.parent.parent
        configRoot = serverRoot / "conf"
        dataRoot   = serverRoot / "data"
        cached     = dataRoot / "cache"

        self.assertEquals(config.ServerRoot, serverRoot)
        self.assertEquals(config.ConfigRoot, configRoot)
        self.assertEquals(config.DataRoot, dataRoot)
        self.assertEquals(config.CachedResourcesPath, cached)

        # self.assertEquals(config.DMSHost, "dms.rangers.example.com")
        self.assertEquals(config.DMSDatabase, "rangers")
        self.assertEquals(config.DMSUsername, "ims")
        self.assertEquals(
            config.DMSPassword, "9F29BB2B-E775-489C-9C20-9FE3EFEE1F22"
        )
