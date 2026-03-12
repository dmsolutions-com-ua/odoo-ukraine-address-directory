==================
Geodata Connector
==================

Integration with Geodata.online API for address autocomplete and normalization in Ukraine.

Features
========

* **Address Autocomplete**: Real-time address suggestions from Geodata.online API
* **Address Normalization**: Standardized address formatting according to Ukrainian standards
* **Wizard UI**: User-friendly wizard for address selection in res.partner forms
* **Automatic Field Population**: Auto-fills street, city, zip, state, and coordinates
* **Multi-language Support**: Ukrainian and Russian language interfaces
* **Multi-company Support**: Works with multiple companies

Installation
============

1. Install dependencies: ``kw_api_connector``, ``kw_http_request_log``, ``kw_mixin``, ``base_geolocalize``
2. Install module from Odoo Apps
3. Configure API credentials in Settings > Address (GEODATA) > API Credentials
4. Obtain API key from https://geodata.online/

Usage
=====

1. Open any res.partner form
2. Click "Address Wizard" button
3. Enter search query (city, street, house number)
4. Select address from results
5. Click "Apply Selected" to auto-fill address fields

Configuration
=============

Navigate to **Settings > Address (GEODATA)**:

- **API Credentials**: Manage Geodata API credentials
- **API Connectors**: Configure API connection settings

Technical Details
=================

- Based on ``kw.api.connector`` framework
- All API requests are logged via ``kw_http_request_log``
- Uses ``@use_fname`` decorator for method dispatch
- Stores address data in ``geodata.address`` model

API Documentation
=================

Geodata.online API documentation: https://documenter.getpostman.com/view/2267163/7E8jGij

License
=======

LGPL-3
