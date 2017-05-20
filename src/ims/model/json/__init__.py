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
Incident Management System data model JSON serialization/deserialization
"""

from . import _address
from . import _entry
from . import _event
from . import _location
from . import _priority
from . import _report
from . import _state
from . import _type
from ._json import jsonTextFromModelObject

del _address
del _entry
del _event
del _location
del _priority
del _report
del _state
del _type


__all__ = (
    "jsonTextFromModelObject",
)
