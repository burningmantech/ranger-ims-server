# -----------------------------------------------------------------------------
# This stage builds the build container.
# -----------------------------------------------------------------------------
FROM python:3.12.3-alpine3.18 AS build

# Install compiler toolchain and libraries.
RUN apk add --no-cache build-base libffi-dev libressl-dev

# Install Rust for cryptography
RUN apk add --no-cache python3-dev rust cargo

# Paths
ARG IMS_SOURCE_DIR="/src/ims"
ARG IMS_INSTALL_DIR="/opt/ims"

# Copy the source code over
WORKDIR "${IMS_SOURCE_DIR}"

COPY ./COPYRIGHT.txt  ./
COPY ./LICENSE.txt    ./
COPY ./MANIFEST.in    ./
COPY ./pyproject.toml ./
COPY ./README.rst     ./
COPY ./requirements/  ./requirements/
COPY ./src/           ./src/
COPY ./uv.lock        ./

# Install the application
WORKDIR /tmp
RUN install -o daemon -g daemon -d "${IMS_INSTALL_DIR}"
RUN pip install --upgrade pip uv
RUN uv venv "${IMS_INSTALL_DIR}"
RUN . "${IMS_INSTALL_DIR}/bin/activate" \
    && uv pip --no-progress install \
        --no-cache --exact --compile-bytecode \
        "${IMS_SOURCE_DIR}"


# -----------------------------------------------------------------------------
# This stage builds the application container.
# -----------------------------------------------------------------------------
FROM python:3.12.3-alpine3.18 AS application

# Paths
ARG IMS_INSTALL_DIR="/opt/ims"
ARG IMS_SERVER_ROOT="/srv/ims"

# Docker-specific default configuration
ENV IMS_HOSTNAME="0.0.0.0"
ENV IMS_CONFIG_ROOT="${IMS_INSTALL_DIR}/conf"
ENV IMS_SERVER_ROOT="${IMS_SERVER_ROOT}"
ENV IMS_DATA_STORE="MySQL"
ENV IMS_DIRECTORY="ClubhouseDB"

# Install libraries.
RUN apk add --no-cache libressl

# Allow Python to bind to privileged port numbers
RUN apk add --no-cache libcap
RUN setcap "cap_net_bind_service=+ep" /usr/local/bin/python3.12

# Create server root and make that our working directory
RUN install -o daemon -g daemon -d "${IMS_SERVER_ROOT}"

# Copy build result
COPY --from=build "${IMS_INSTALL_DIR}" "${IMS_INSTALL_DIR}"

# Set user and default working directory
USER daemon:daemon
WORKDIR "${IMS_SERVER_ROOT}"

# Expose service port
EXPOSE 80

# Default command
CMD [ "/opt/ims/bin/ims", "--log-file", "-", "server" ]
