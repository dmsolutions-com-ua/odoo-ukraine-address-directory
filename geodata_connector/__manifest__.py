{
    "name": "Ukraine Address Reference Directory",
    "summary": """
        Integration with Geodata.online API for address autocomplete
        and normalization in Ukraine
    """,
    "author": "GEODATA.online",
    "website": "https://geodata.online",
    "category": "Hidden",
    "license": "LGPL-3",
    "version": "18.0.2.0.0",
    "depends": [
        "base",
        "base_geolocalize",
        "kw_api_connector",
    ],
    "external_dependencies": {
        "python": [],
    },
    "data": [
        "security/geodata_security.xml",
        "security/ir.model.access.csv",
        "data/base_geo_provider.xml",
        "data/geodata_api_connector.xml",
        "data/http_request_log_source.xml",
        "views/geodata_api_credential_views.xml",
        "views/geodata_api_connector_views.xml",
        "views/geodata_address_views.xml",
    ],
    "demo": [
        # 'demo/credential.xml',
    ],
    "assets": {
        "web.assets_backend": [
            "geodata_connector/static/src/scss/*",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": False,
    "post_init_hook": "post_init_hook",
    "images": [
        "static/description/cover.png",
        "static/description/icon.png",
    ],
}
