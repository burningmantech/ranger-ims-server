Ranger Incident Management System
=================================

.. image:: https://github.com/burningmantech/ranger-ims-server/workflows/.github/workflows/cicd.yml/badge.svg
    :target: https://github.com/burningmantech/ranger-ims-server/actions
    :alt: Build Status
.. image:: https://codecov.io/github/burningmantech/ranger-ims-server/coverage.svg?branch=master
    :target: https://codecov.io/github/burningmantech/ranger-ims-server?branch=master
    :alt: Code Coverage
.. image:: https://requires.io/github/burningmantech/ranger-ims-server/requirements.svg?branch=master
    :target: https://requires.io/github/burningmantech/ranger-ims-server/requirements/?branch=master
    :alt: Requirements Status

This software package implements software to provide logging for incidents as they occur and to aid in the dispatch of resources to respond to those incidents.
It is presently tailored to the specific needs of the Black Rock Rangers in Black Rock City.

The server is the master (authoritative) repository for incident information.
Clients connect to the server over the network and provide an interface to users which enables them to view and manage incident information.

This package provides the server component, which includes a web client and some web-based reporting features.
All functionality is expose via JSON endpoints.

The server is implemented using Twisted_ Klein_ and requires Python 3.6.


Development
-----------

This project uses Tox_ for running tests.
To run all of the default test environments::

    tox

To run the server (for development only)::

    tox -e run

Pull requests in GitHub will run Flake8, Mypy, and unit tests on Travis CI, and all are required to pass prior to merging.

100% unit test coverage is also expected for all new or modified code prior to merging a pull request.


.. ------------------------------------------------------------------------- ..

.. _Twisted: https://twistedmatrix.com/
.. _Klein: https://klein.readthedocs.io/
.. _Tox: http://tox.readthedocs.io/
.. _Flake8: http://flake8.pycqa.org/
.. _Mypy: http://mypy.readthedocs.io/
