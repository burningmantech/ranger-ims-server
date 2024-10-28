#!/usr/bin/env python

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
Setuptools configuration
"""

from pathlib import Path

from setuptools import find_packages, setup


#
# Options
#

project_root = Path(__file__).parent

packages = find_packages(where="src")


#
# Package data
#

package_data = dict(
    ims=[
        "config/test/*.conf",
        "directory/file/test/directory.yaml",
        "element/*/template.xhtml",
        "element/*/*/template.xhtml",
        "element/static/*.css",
        "element/static/*.js",
        "element/static/*.png",
        "element/static/*.zip",
        "store/mysql/schema/*.mysql",
        "store/sqlite/schema/*.sqlite",
    ],
)


#
# Dependencies
#


def read_requirements(path: Path) -> list[str]:
    """
    Parse requirements file.
    """
    return [
        requirement
        for requirement in (
            line.split("#", 1)[0].strip() for line in path.open()
        )
        if requirement
    ]


python_requirements = ">=3.12"

setup_requirements: list[str] = []

requirements_dir = project_root / "requirements"
install_requirements = read_requirements(
    requirements_dir / "requirements-direct.txt"
) + read_requirements(requirements_dir / "requirements-indirect.txt")

extras_requirements: dict[str, str] = {}


#
# Run setup
#


def main() -> None:
    """
    Run :func:`setup`.
    """
    setup(
        packages=packages,
        package_dir={"": "src"},
        package_data=package_data,
        data_files=[],
    )


#
# Main
#

if __name__ == "__main__":
    main()
