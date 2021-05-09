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

import sys
from pathlib import Path
from typing import Dict, List, Optional

from setuptools import find_packages, setup

sys.path.insert(0, "src")

from ims import __version__ as version_string  # noqa: E402


#
# Options
#

name = "ranger-ims-server"

description = "Ranger Incident Management System"

readme_path = Path(__file__).parent / "README.rst"
try:
    long_description: Optional[str] = readme_path.open().read()
except OSError:
    long_description = None

url = "https://github.com/burningmantech/ranger-ims-server"

author = "Burning Man"

author_email = "rangers@burningman.org"

license = "Apache License, Version 2.0"

platforms = ["all"]

packages = find_packages(where="src")

classifiers = [
    "Framework :: Twisted",
    "Intended Audience :: Information Technology",
    "Intended Audience :: Other Audience",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3.9",
    "Topic :: Office/Business",
]


#
# Entry points
#

entry_points = dict(console_scripts=["ims = ims.run:Command.main"])


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

python_requirements = ">=3.9"

setup_requirements: List[str] = []

install_requirements = [
    # Direct dependencies
    "arrow==1.1.0",
    "attrs==21.2.0",
    "bcrypt==3.2.0",
    "cattrs==1.6.0",
    "hyperlink==21.0.0",
    "klein==20.6.0",
    "PyMySQL==1.0.2",
    "pyOpenSSL==20.0.1",
    "PyYAML==5.4.1",
    "service-identity==21.1.0",
    "Twisted==21.2.0",
    "zope.interface==5.4.0",
    # Indirect dependencies
    "Automat==20.2.0",
    "cffi==1.14.5",
    "characteristic==14.3.0",
    "constantly==15.1.0",
    "cryptography==3.4.7",
    "idna==3.1",
    "incremental==21.3.0",
    "pyasn1==0.4.8",
    "pyasn1-modules==0.2.8",
    "pycparser==2.20",
    "PyHamcrest==2.0.2",
    "python-dateutil==2.8.1",
    "six==1.16.0",
    "Tubes==0.2.0",
    "Werkzeug==1.0.1",
]

extras_requirements: Dict[str, str] = {}


#
# Set up Extension modules that need to be built
#

extensions: List[str] = []


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
