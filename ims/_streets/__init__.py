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
    "concentricStreetNumberByName",
    "concentricStreetNameByNumber",
]

from ._2015 import concentricStreetNumberByName as _2015



concentricStreetNumberByName = {
    "2015": _2015,
}

concentricStreetNameByNumber = {
    "2015": {v: k for k, v in _2015.items()},
}
