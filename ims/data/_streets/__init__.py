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
BRC Street Names
"""

__all__ = [
    "concentricStreetIDByName",
    "concentricStreetNameByID",
]

from ._2013 import concentricStreetIDByName as _2013
from ._2014 import concentricStreetIDByName as _2014
from ._2015 import concentricStreetIDByName as _2015



concentricStreetIDByName = {
    "2013": _2013,
    "2014": _2014,
    "2015": _2015,
    "Test": _2015,
}

concentricStreetNameByID = {
    "2013": {v: k for k, v in _2013.items()},
    "2014": {v: k for k, v in _2014.items()},
    "2015": {v: k for k, v in _2015.items()},
    "Test": {v: k for k, v in _2015.items()},
}
