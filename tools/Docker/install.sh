#!/bin/sh

##
# Install the IMS server into a Docker container
##

set -e
set -u

install_dir="/docker_install";

apk --no-cache add  \
    build-base      \
    libffi-dev      \
    openssl-dev     \
    ;

pip install                              \
    --no-cache-dir                       \
    --find-links "${install_dir}/sdist"  \
    ranger-ims-server                    \
    ;

apk del             \
    build-base      \
    libffi-dev      \
    openssl-dev     \
    ;

rm -rf "${install_dir}";
