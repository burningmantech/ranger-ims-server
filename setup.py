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
    "server"      : ("ims.run", "Server.main"),
    # "endpoints"   : ("ims.legacy.service.tool", "KleinTool.main"),
    # "schema"      : ("ims.store.sqlite", "DataStore.printSchema"),
    # "queries"     : ("ims.store.sqlite", "DataStore.printQueries"),
    # "load_legacy" : ("ims.legacy.service.tool", "LegacyLoadTool.main"),
    # "load_json"   : ("ims.legacy.service.tool", "JSONLoadTool.main"),
}

for tool, (module, function) in script_entry_points.items():
    entry_points["console_scripts"].append(
        "ims_{} = {}:{}".format(tool, module, function)
    )


#
# Package data
#

package_data = dict(
    ims = [
        "config/test/*.conf",
        "element/*/template.xhtml",
        "element/static/*.css",
        "element/static/*.js",
        "element/static/*.png",
        "store/sqlite/schema.*.sqlite",
    ],
)


#
# Dependencies
#

setup_requirements = []

install_requirements = [
    "arrow==0.10.0",
    "attrs==17.2.0",
    "Automat==0.6.0",
    "cattrs==0.4.0",
    "constantly==15.1.0",
    "hyperlink==17.3.0",
    "incremental==17.5.0",
    "klein==17.2.0",
    "PyMySQL==0.7.11",
    "pyOpenSSL==17.2.0",
    "python-dateutil==2.6.1",
    "ranger-ims-server==1.0",
    "six==1.10.0",
    #"Twisted>=17.5.0",
    "Werkzeug==0.12.2",
    "zope.interface==4.4.2",
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
        setup_requires=setup_requirements,
        install_requires=install_requirements,
        extras_require=extras_requirements,
    )


#
# Main
#

if __name__ == "__main__":
    main()
