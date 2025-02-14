Ranger Incident Management System
=================================

.. image:: https://github.com/burningmantech/ranger-ims-server/workflows/CI%2fCD/badge.svg
    :target: https://github.com/burningmantech/ranger-ims-server/actions
    :alt: Build Status
.. image:: https://codecov.io/github/burningmantech/ranger-ims-server/coverage.svg?branch=master
    :target: https://codecov.io/github/burningmantech/ranger-ims-server?branch=master
    :alt: Code Coverage

This software package implements software to provide logging for incidents as they occur and to aid in the dispatch of resources to respond to those incidents.
It is presently tailored to the specific needs of the Black Rock Rangers in Black Rock City.

The server is the master (authoritative) repository for incident information.
Clients connect to the server over the network and provide an interface to users which enables them to view and manage incident information.

This package provides the server component, which includes a web client and some web-based reporting features.
All functionality is exposed via JSON endpoints.

The server is implemented using Twisted_ Klein_ and requires Python 3.9+.


Development
-----------

This project requires uv_ and pre-commit_ for development and Tox_ and running tests.

If you do not have uv installed, see the uv documentation for instructions.

If you do not have pre-commit and/or tox installed, use uv. Be sure to include the tox-uv_ plugin::

    uv tool install pre-commit
    pre-commit install
    uv tool install tox --with tox-uv

The ``pre-commit install`` step installs a Git hook which runs pre-commit automatically when you run ``git commit``.
This is very useful as a measure to prevent commits that would later fail during CI builds.

To run all of the default test environments::

    tox run

Running the Server
~~~~~~~~~~~~~~~~~~

--------------------
With docker-compose
--------------------

First, get the configuration set up::

    # These files are mounted into the container
    ``cp conf/imsd-docker-compose-sample.conf conf/imsd.conf``
    ``cp conf/directory-sample.yaml conf/directory.yaml``
    ``cp .docker/sampe.env ./.env``

Set appropriate overrides in `.env` or `conf/imsd.conf` where appropriate.

Start the server::

    Production
        ``docker compose up`` or ``docker compose up -d`` to run in daemon mode (no console output)

    Development
        ``docker compose up --watch``
            In watch mode saving files in the application directory will restart the server. You will
            still need to refresh the browser, but this will be faster than manually restarting & rebuilding
            the server when changes are made.

        ``docker compose down; docker compose build dev; docker compose up --watch`` will force a full rebuild of the app.




------------------
Outside docker
------------------

To run the server will require some configuration, and if you try to start the server with the default configuration, you will probably see an error such as this::

    2020-03-12T09:16:55-0700 [ims.run._command.Command#info] Setting up web service at http://localhost:80/
    2020-03-12T09:16:55-0700 [ims.run._command.Command#critical] Unable to run server: Couldn't listen on localhost:80: [Errno 13] Permission denied.
    2020-03-12T09:16:55-0700 [-] Main loop terminated.

The above error happens because the server, by default, tries to use the standard port for HTTP (80), and that is commonly reserved for system services.

To set up a configuration for development, start by copying the example configuration and directory files::

    cp conf/imsd-sample.conf conf/imsd.conf
    cp conf/directory-sample.yaml conf/directory.yaml

To build and run the server (for development only)::

    uv run ims --log-file=- --config=./conf/imsd.conf server
    # or, with debug log-level:
    uv run ims --log-file=- --config=./conf/imsd.conf --log-level=debug server

---------------------
Settings Permissions
---------------------

In your browser, open http://localhost:8080/ to reach the server. Log in as any user in the ``conf/directory.yaml`` directory file.
In the ``conf/imsd-sample.conf`` sample configuration file, the users ``Hardware`` and ``Loosy`` are administrators, and in the sample directory, all users have passwords that match their handles.
You'll want to log in as one of those to set up an Event.

Use the pull-down menu at the top right corner of the page (it will show the logged in user's Ranger handle), and select ``Admin``.
On the next page, navigate to the Events page and create an event called ``Test``.

In the box labeled ``Access for Test (writers)``, enter the string ``*``.
That will give all users the ability to create and edit incidents in that event.

You should now be able to select your new event from the ``Event`` menu at the top right, and then create new incidents within that event.


Pull Requests
~~~~~~~~~~~~~

Pull requests in GitHub will run all tests on Travis CI, and all are required to pass prior to merging.

100% unit test coverage is also expected for all new or modified code prior to merging a pull request.

.. ------------------------------------------------------------------------- ..

.. _Klein: https://klein.readthedocs.io/
.. _Mypy: http://mypy.readthedocs.io/
.. _pre-commit: https://pre-commit.com/
.. _tox-uv: https://github.com/tox-dev/tox-uv
.. _Tox: http://tox.readthedocs.io/
.. _Twisted: https://twistedmatrix.com/
.. _uv: https://docs.astral.sh/uv/
