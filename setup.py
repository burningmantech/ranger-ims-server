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

if sys.version_info < (3, 6, 0):
    sys.stderr.write("ERROR: Python 3.6 or later is required.\n")
    exit(1)

from pathlib import Path  # noqa
from setuptools import setup, find_packages  # noqa

sys.path.insert(0, "src")

from ims import __version__ as version_string  # noqa


#
# Options
#

name = "ranger-ims-server"

description = "Ranger Incident Management System"

readme_path = Path(__file__).parent / "README.rst"
try:
    long_description = readme_path.open().read()
except IOError:
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
    "Programming Language :: Python :: 3.6",
    "Topic :: Office/Business",
]


#
# Entry points
#

entry_points = {
    "console_scripts": [],
}

script_entry_points = {
    "server"      : ("ims.run", "Command.main"),
    # "endpoints"   : ("ims.legacy.service.tool", "KleinTool.main"),
    # "schema"      : ("ims.store.sqlite", "DataStore.printSchema"),
    # "queries"     : ("ims.store.sqlite", "DataStore.printQueries"),
}

for tool, (module, function) in script_entry_points.items():
    entry_points["console_scripts"].append(f"ims_{tool} = {module}:{function}")


#
# Package data
#

package_data = dict(
    ims=[
        "config/test/*.conf",
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

python_requirements = ">=3.6,<3.8"

setup_requirements = []

install_requirements = [
    # Direct dependencies
    "arrow==0.15.4",
    "attrs==19.3.0",
    "cattrs==1.0.0",
    "hyperlink==19.0.0",
    "klein==19.6.0",
    "PyMySQL==0.9.3",
    "Twisted==19.10.0",
    "zope.interface==4.7.1",
    "pyOpenSSL==19.1.0",
    "service-identity==18.1.0",

    # Indirect dependencies
    "asn1crypto==1.2.0",
    "Automat==0.8.0",
    "cffi==1.13.2",
    "constantly==15.1.0",
    "cryptography==2.8",
    "idna==2.8",
    "incremental==17.5.0",
    "pyasn1-modules==0.2.7",
    "pyasn1==0.4.8",
    "pycparser==2.19",
    "PyHamcrest==1.9.0",
    "python-dateutil==2.8.1",
    "ranger-ims-server==18.0.0.dev0",
    "six==1.13.0",
    "Werkzeug==0.16.0",
]

extras_requirements = {}


#
# Set up Extension modules that need to be built
#

extensions = []


#
# Run setup
#

def main():
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
