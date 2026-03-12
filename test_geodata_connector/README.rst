====================================
Geodata Connector Testing Module
====================================

Overview
========

This module provides testing infrastructure for the ``geodata_connector`` module, including:

- Mock API response model for testing without real API calls
- Integration tests (19 test cases)
- Demo data for testing purposes
- Testing documentation

Purpose
=======

The ``test_geodata_connector`` module is designed to:

1. Separate testing concerns from the main geodata_connector module
2. Provide mock functionality for testing without making real API calls
3. Enable comprehensive testing of all geodata_connector features
4. Maintain demo data for development and testing environments

Components
==========

Mock API Response Model
-----------------------

The ``geodata.api.response.mock`` model allows saving and retrieving mock API responses for testing.

Integration Tests
-----------------

Located in ``tests/test_geodata_integration.py``, covering:

- API credential functionality
- Address search methods (cities, streets, full address)
- Wizard functionality and workflows
- Partner integration
- Error handling

Demo Data
---------

- ``geodata_api_credential_demo.xml``: Demo API credentials (inactive by default)
- ``geodata_address_demo.xml``: Sample addresses for Kyiv, Kharkiv, and Lviv

Installation
============

::

    odoo-helper addons install test_geodata_connector

Note: This module requires ``geodata_connector`` to be installed first.

Running Tests
=============

Run all tests::

    odoo-helper test -m test_geodata_connector

Run with coverage::

    odoo-helper test --coverage -m test_geodata_connector

Dependencies
============

- ``geodata_connector``: Main module being tested

License
=======

LGPL-3
