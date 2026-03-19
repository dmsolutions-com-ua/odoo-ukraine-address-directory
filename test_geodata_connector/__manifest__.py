{
    "name": "Geodata Connector Testing",
    "summary": """
        Testing module for geodata_connector with mock data and tests
    """,
    "author": "GEODATA.online",
    "website": "https://geodata.online",
    "category": "Hidden",
    "license": "LGPL-3",
    "version": "18.0.1.0.0",
    "depends": [
        "geodata_connector",
        "geodata_contact",
    ],
    "external_dependencies": {
        "python": [],
    },
    "data": [
        "security/ir.model.access.csv",
        "demo/geodata_api_credential_demo.xml",
        "demo/geodata_address_demo.xml",
    ],
    "assets": {
        "web.assets_tests": [
            "test_geodata_connector/static/tests/" "tours/geodata_autocomplete_tour.js",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": False,
    "images": [
        "static/description/cover.png",
        "static/description/icon.png",
    ],
}
