Ranger Incident Management System
=================================

.. image:: https://api.travis-ci.org/burningmantech/ranger-ims-server.svg?branch=master
    :target: https://travis-ci.org/burningmantech/ranger-ims-server
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

The server is implemented using Twisted_ Klein_ and requires Python 3.6 or later.


Development
-----------

This project uses Tox_ for running tests.
The following Tox environments are defined:

To run the Flake8_ linter::

    tox -e flake8

To run the Mypy_ type checker::

    tox -e mypy

To run the unit tests with coverage reporting for Python 3.6::

    tox -e coverage-py36

To run unit tests for a specific module::

    tox -e coverage-py36 ims.model

To run all environments::

    tox

Pull requests in GitHub will run Flake8, Mypy, and unit tests on Travis CI, and all are required to pass prior to merging.

100% unit test coverage is also expected for all new or modified code prior to merging a pull request.


.. ------------------------------------------------------------------------- ..

.. _Twisted: https://twistedmatrix.com/
.. _Klein: https://klein.readthedocs.io/
.. _Tox: http://tox.readthedocs.io/
.. _Flake8: http://flake8.pycqa.org/
.. _Mypy: http://mypy.readthedocs.io/
