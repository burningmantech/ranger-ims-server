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
Incident report page template.
"""

from .base import Element


__all__ = (
    "IncidentReportTemplatePage",
)



class IncidentReportTemplatePage(Element):
    """
    Incident report page template.
    """

    def __init__(self, service):
        Element.__init__(
            self, "report_template", service, title="Incident Report Details"
        )
