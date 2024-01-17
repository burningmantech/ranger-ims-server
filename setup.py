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
from sys import path

from setuptools import find_packages, setup


path.insert(0, "src")

from ims import __version__ as version_string  # noqa: E402


#
# Options
#

name = "ranger-ims-server"

description = "Ranger Incident Management System"

project_root = Path(__file__).parent

readme_path = project_root / "README.rst"
long_description = readme_path.open().read()

url = "https://github.com/burningmantech/ranger-ims-server"

author = "Burning Man Project, Black Rock Rangers"

author_email = "ranger-tech-ninjas@burningman.org"

license = "Apache License, Version 2.0"

platforms = ["all"]

packages = find_packages(where="src")

classifiers = [
    "Framework :: Twisted",
    "Intended Audience :: Information Technology",
    "Intended Audience :: Other Audience",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Topic :: Office/Business",
]


#
# Entry points
#

entry_points = {
    "console_scripts": ["ims = ims.run:Command.main"],
}


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


python_requirements = ">=3.9"

setup_requirements: list[str] = []

requirements_dir = project_root / "requirements"
install_requirements = read_requirements(
    requirements_dir / "requirements-direct.txt"
) + read_requirements(requirements_dir / "requirements-indirect.txt")

extras_requirements: dict[str, str] = {}


#
# Set up Extension modules that need to be built
#

extensions: list[str] = []


#
# Run setup
#


def main() -> None:
    """
    Run :func:`setup`.
    """
    setup(
        name=name,
        version=version_string,
        description=description,
        long_description=long_description,
        long_description_content_type="text/x-rst",
        url=url,
        classifiers=classifiers,
        author=author,
        author_email=author_email,
        license=license,
        platforms=platforms,
        packages=packages,
        package_dir={"": "src"},
        package_data=package_data,
        entry_points=entry_points,
        data_files=[],
        ext_modules=extensions,
        python_requires=python_requirements,
        setup_requires=setup_requirements,
        install_requires=install_requirements,
        extras_require=extras_requirements,
    )


#
# Main
#

if __name__ == "__main__":
    main()
