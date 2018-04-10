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

setup_requirements = []

install_requirements = [
    # Direct dependencies
    "arrow==0.12.1",
    "attrs==17.4.0",
    "cattrs==0.4.0",
    "hyperlink==18.0.0",
    "klein==17.10.0",
    "PyMySQL==0.8.0",
    "pyOpenSSL==17.5.0",
    "service_identity==17.0.0",
    "Twisted==17.9.0",
    "zope.interface==4.4.3",

    # Indirect dependencies
    "asn1crypto==0.24.0",
    "Automat==0.6.0",
    "certifi==2018.1.18",
    "cffi==1.11.5",
    "chardet==3.0.4",
    "constantly==15.1.0",
    "coverage==4.4.2",
    "cryptography==2.2.2",
    "docker==3.2.1",
    "docker-pycreds==0.2.2",
    "hypothesis==3.44.14",
    "idna==2.6",
    "incremental==17.5.0",
    "mock==2.0.0",
    "pbr==4.0.1",
    "pyasn1==0.4.2",
    "pyasn1-modules==0.2.1",
    "pycparser==2.18",
    "pyOpenSSL==17.5.0",
    "python-dateutil==2.7.2",
    "ranger-ims-server==18.0.0.dev0",
    "requests==2.18.4",
    "six==1.11.0",
    "urllib3==1.22",
    "websocket-client==0.47.0",
    "Werkzeug==0.14.1",
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
