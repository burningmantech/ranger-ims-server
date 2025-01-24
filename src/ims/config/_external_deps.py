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
Incident Management System external dependency versions.
"""

from attrs import frozen
from hyperlink import URL


__all__ = ()


@frozen(kw_only=True)
class ExternalDeps:
    bootstrapVersionNumber = "5.3.3"
    bootstrapJsIntegrity = "sha512-7Pi/otdlbbCR+LnW+F7PwFcSDJOuUJB3OxtEHbg4vSMvzvJjde4Po1v4BR9Gdc9aXNUNFVUY+SK51wWT8WF0Gg=="  # noqa: E501

    jqueryVersionNumber = "3.1.0"
    jqueryJsIntegrity = "sha512-qzrZqY/kMVCEYeu/gCm8U2800Wz++LTGK4pitW/iswpCbjwxhsmUwleL1YXaHImptCHG0vJwU7Ly7ROw3ZQoww=="  # noqa: E501

    dataTablesVersionNumber = "2.1.8"
    dataTablesJsIntegrity = "sha512-aB+KD1UH6xhwz0ZLqIGK+if/B83XzgnFzDJtf195axOEqurA7ahWCpl8wgXWVfcMslhnmYigAjYXShrJSlxgWg=="  # noqa: E501
    dataTablesBootstrap5JsIntegrity = "sha512-Cwi0jz7fz7mrX990DlJ1+rmiH/D9/rjfOoEex8C9qrPRDDqwMPdWV7pJFKzhM10gAAPlufZcWhfMuPN699Ej0w=="  # noqa: E501

    bootstrapVersion = f"bootstrap-{bootstrapVersionNumber}-dist"
    jqueryVersion = f"jquery-{jqueryVersionNumber}"
    dataTablesVersion = f"DataTables-{dataTablesVersionNumber}"

    bootstrapSourceURL = URL.fromText(
        f"https://github.com/twbs/bootstrap/releases/download/"
        f"v{bootstrapVersionNumber}/{bootstrapVersion}.zip"
    )

    jqueryJSSourceURL = URL.fromText(
        f"https://cdnjs.cloudflare.com/ajax/libs/jquery/"
        f"{jqueryVersionNumber}/jquery.min.js"
    )

    jqueryMapSourceURL = URL.fromText(
        f"https://cdnjs.cloudflare.com/ajax/libs/jquery/"
        f"{jqueryVersionNumber}/jquery.min.map"
    )

    dataTablesSourceURL = URL.fromText(
        f"https://datatables.net/releases/DataTables-{dataTablesVersionNumber}.zip"
    )
