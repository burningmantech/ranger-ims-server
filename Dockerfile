FROM python:3.6-alpine3.7 as build
# -----------------------------------------------------------------------------
# This stage builds the build container.
# -----------------------------------------------------------------------------

WORKDIR /src/ims

# Install compiler toolchain and libraries.
RUN apk add build-base libffi-dev

# Install/upgrade pip and virtualenv
RUN pip install --upgrade pip virtualenv

# Copy the source code over
COPY ./COPYRIGHT.rst  ./
COPY ./LICENSE.txt    ./
COPY ./pyproject.toml ./
COPY ./setup.py       ./
COPY ./src/           ./src/

# Install the application
RUN virtualenv /srv/ims
RUN /srv/ims/bin/pip install /src/ims
RUN rm -rf /src


# -----------------------------------------------------------------------------
# This stage builds the application container.
# -----------------------------------------------------------------------------
FROM python:3.6-alpine3.7 as application

COPY --from=build /srv/ims /srv/ims

WORKDIR /srv/ims

EXPOSE 8080

CMD [                                       \
    "/srv/ims/bin/ims_server",              \
    "--config", "/srv/ims/conf/imsd.conf",  \
    "--log-file", "-"                       \
]
