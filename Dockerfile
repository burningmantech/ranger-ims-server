FROM python:3.6-alpine3.7 as build
# -----------------------------------------------------------------------------
# This stage builds the build container.
# -----------------------------------------------------------------------------

# Install compiler toolchain and libraries.
RUN apk add build-base libffi-dev libressl-dev

# Install/upgrade pip and virtualenv
RUN pip install --upgrade pip virtualenv

# Copy the source code over
WORKDIR /src/ims

COPY ./COPYRIGHT.rst  ./
COPY ./LICENSE.txt    ./
COPY ./pyproject.toml ./
COPY ./setup.py       ./
COPY ./src/           ./src/

# Install the application
WORKDIR /tmp
RUN install -o daemon -g daemon -d /opt/ims
USER daemon:daemon
RUN virtualenv /opt/ims
RUN /opt/ims/bin/pip --no-cache-dir install /src/ims


# -----------------------------------------------------------------------------
# This stage builds the application container.
# -----------------------------------------------------------------------------
FROM python:3.6-alpine3.7 as application

COPY --from=build /opt/ims /opt/ims

RUN install -o daemon -g daemon -d /srv/ims
WORKDIR /srv/ims
USER daemon:daemon

EXPOSE 8080

CMD [                                       \
    "/opt/ims/bin/ims_server",              \
    "--config", "/srv/ims/conf/imsd.conf",  \
    "--log-file", "-"                       \
]
