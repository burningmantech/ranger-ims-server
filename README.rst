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

The server is implemented using Klein_.

.. ------------------------------------------------------------------------- ..

.. _Klein: https://github.com/twisted/klein/
