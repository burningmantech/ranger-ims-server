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
Distutils setup.
"""

from __future__ import print_function

from os.path import dirname, join as joinpath
from setuptools import setup, find_packages as find_packages



#
# Utilities
#

def version():
    """
    Compute the version number.
    """
    base_version = "0.2b"

    full_version = base_version

    return full_version



#
# Options
#

name = "ranger-ims"

description = "Ranger Incident Management System"

long_description = file(joinpath(dirname(__file__), "README.md")).read()

url = "https://github.com/burningmantech/ranger-ims"

classifiers = [
    "Development Status :: 3 - Alpha",
    "Framework :: Twisted",
    "Intended Audience :: Information Technology",
    "Intended Audience :: Other Audience",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 2 :: Only",
    "Topic :: Office/Business",
]

author = "Wilfredo S\xe1nchez Vega"

author_email = "tool@burningman.com"

license = "Apache License, Version 2.0"

platforms = ["all"]



#
# Entry points
#

entry_points = {
    "console_scripts": [],
}

script_entry_points = {
}

for n, (m, f) in script_entry_points.iteritems():
    entry_points["console_scripts"].append(
        "calendarserver_{} = {}:{}".format(n, m, f)
    )



#
# Dependencies
#

setup_requirements = []

install_requirements = [
    "Twisted",
    "klein",
    "pyOpenSSL", "service_identity",
    "mysql-connector-python",
]

extras_requirements = {
}



#
# Set up Extension modules that need to be built
#

extensions = []



#
# Run setup
#

def doSetup():
    """
    Run L{setup}.
    """
    # Write version file
    version_string = version()
    version_filename = joinpath(dirname(__file__), "ims", "version.py")
    version_file = file(version_filename, "w")

    try:
        version_file.write(
            'version = "{0}"\n'.format(version_string)
        )
    finally:
        version_file.close()

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
        packages=find_packages(),
        package_data={},
        entry_points=entry_points,
        scripts=["bin/imsd"],
        data_files=[],
        ext_modules=extensions,
        py_modules=[],
        setup_requires=setup_requirements,
        install_requires=install_requirements,
        extras_require=extras_requirements,
    )



#
# Main
#

if __name__ == "__main__":
    doSetup()
