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
Tests for L{ims.config}.
"""

from twisted.python.filepath import FilePath
import twisted.trial.unittest

from ..config import Configuration



sourceRoot = FilePath(__file__).parent().parent().parent().parent()

emptyConfigFile  = FilePath("/dev/null")
sampleConfigFile = sourceRoot.child("conf").child("imsd-sample.conf")



class ConfigurationTests(twisted.trial.unittest.TestCase):
    """
    Tests for L{ims.config.Configuration}
    """

    def test_defaults(self):
        """
        Check defaults.
        """
        config = Configuration(emptyConfigFile)

        serverRoot = FilePath("/")
        configRoot = serverRoot.child("conf")
        dataRoot   = serverRoot.child("data")
        cached     = serverRoot.child("cached")

        self.assertEquals(config.ServerRoot, serverRoot)
        self.assertEquals(config.ConfigRoot, configRoot)
        self.assertEquals(config.UserDB, configRoot.child("users.pwdb"))
        self.assertEquals(config.DataRoot, dataRoot)
        self.assertEquals(config.CachedResources, cached)

        self.assertEquals(config.DMSHost, None)
        self.assertEquals(config.DMSDatabase, None)
        self.assertEquals(config.DMSUsername, None)
        self.assertEquals(config.DMSPassword, None)


    def test_sampleConfig(self):
        """
        Check sample config.
        """
        config = Configuration(sampleConfigFile)

        serverRoot = sourceRoot
        configRoot = serverRoot.child("conf")
        dataRoot   = serverRoot.child("data")
        cached     = serverRoot.child("cached")

        self.assertEquals(config.ServerRoot, serverRoot)
        self.assertEquals(config.ConfigRoot, configRoot)
        self.assertEquals(config.UserDB, configRoot.child("users.pwdb"))
        self.assertEquals(config.DataRoot, dataRoot)
        self.assertEquals(config.CachedResources, cached)

        self.assertEquals(config.DMSHost, "dms.rangers.example.com")
        self.assertEquals(config.DMSDatabase, "rangers")
        self.assertEquals(config.DMSUsername, "ims")
        self.assertEquals(
            config.DMSPassword, "9F29BB2B-E775-489C-9C20-9FE3EFEE1F22"
        )
