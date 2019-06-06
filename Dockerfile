FROM python:3.6-alpine3.7 as build
# -----------------------------------------------------------------------------
# This stage builds the build container.
# -----------------------------------------------------------------------------

# Install compiler toolchain and libraries.
RUN apk add --no-cache build-base libffi-dev libressl-dev

# Install/upgrade pip and virtualenv
RUN pip install --upgrade pip virtualenv

# Paths
ENV IMS_SOURCE_DIR="/src/ims"
ENV IMS_INSTALL_DIR="/opt/ims"

# Copy the source code over
WORKDIR "${IMS_SOURCE_DIR}"

COPY ./COPYRIGHT.rst  ./
COPY ./LICENSE.txt    ./
COPY ./pyproject.toml ./
COPY ./setup.py       ./
COPY ./src/           ./src/

# Install the application
WORKDIR /tmp
RUN install -o daemon -g daemon -d "${IMS_INSTALL_DIR}"
USER daemon:daemon
RUN virtualenv "${IMS_INSTALL_DIR}"
RUN "${IMS_INSTALL_DIR}/bin/pip" --no-cache-dir install "${IMS_SOURCE_DIR}"


# -----------------------------------------------------------------------------
# This stage builds the application container.
# -----------------------------------------------------------------------------
FROM python:3.6-alpine3.7 as application

# Copy build result
ENV IMS_INSTALL_DIR="/opt/ims"
COPY --from=build "${IMS_INSTALL_DIR}" "${IMS_INSTALL_DIR}"

# Allow ims_server to bind to privileged port numbers
RUN apk add --no-cache libcap
RUN setcap "cap_net_bind_service=+ep" "${IMS_INSTALL_DIR}/bin/python"

# Configuration
ENV IMS_HOSTNAME="0.0.0.0"
ENV IMS_CONFIG_ROOT="${IMS_INSTALL_DIR}/conf"
ENV IMS_SERVER_ROOT="/srv/ims"
ENV IMS_DATA_STORE="MySQL"

RUN install -o daemon -g daemon -d "${IMS_SERVER_ROOT}"
WORKDIR "${IMS_SERVER_ROOT}"
USER daemon:daemon

EXPOSE 80

CMD [ "/opt/ims/bin/ims_server", "--log-file", "-" ]
