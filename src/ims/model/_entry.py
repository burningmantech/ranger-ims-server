# -*- test-case-name: ranger-ims-server.model.test.test_entry -*-

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
Report entry
"""

from datetime import datetime as DateTime
from typing import Any

from attr import attrib, attrs

from ._cmp import ComparisonMixIn
from ._convert import normalizeDateTime
from ._replace import ReplaceMixIn


__all__ = ()



@attrs(frozen=True, auto_attribs=True, kw_only=True, eq=False)
class ReportEntry(ComparisonMixIn, ReplaceMixIn):
    """
    Report entry

    A report entry is text with an associated author and time stamp.
    """

    created: DateTime = attrib(converter=normalizeDateTime)
    author: str
    automatic: bool
    text: str


    def __str__(self) -> str:
        if self.automatic:
            automatic = "*"
        else:
            automatic = ""

        return f"{self.created} {self.author}{automatic}: {self.text}"


    def _cmpValue(self) -> Any:
        return (self.created, self.author, not self.automatic, self.text)
