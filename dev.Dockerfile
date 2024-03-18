# -----------------------------------------------------------------------------
# This stage builds the development container.
# -----------------------------------------------------------------------------
FROM python:3.12.1-alpine3.18 as development

# Paths
ARG IMS_SERVER_ROOT="/srv/ims"

# Install libraries.
RUN apk add --no-cache libressl
RUN pip install --upgrade setuptools
RUN pip install --upgrade tox
RUN rm -rf /root/.cache

# Allow Python to bind to privileged port numbers
RUN apk add --no-cache libcap
RUN setcap "cap_net_bind_service=+ep" /usr/local/bin/python3.12

# Set user and default working directory
USER daemon:daemon
WORKDIR "${IMS_SERVER_ROOT}"
