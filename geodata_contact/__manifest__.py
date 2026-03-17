{
    "name": "Ukraine Address Integration - Contacts",
    "summary": """
        Integrates Geodata.online addresses with contact forms
    """,
    "author": "GEODATA.online",
    "website": "https://geodata.online",
    "category": "Technical",
    "license": "LGPL-3",
    "version": "18.0.2.0.0",
    "depends": [
        "geodata_connector",
        "contacts",
        "kw_widget_autocomplete",
    ],
    "external_dependencies": {
        "python": [],
    },
    "data": [
        "security/ir.model.access.csv",
        "views/res_partner_views.xml",
        "views/geodata_address_wizard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "geodata_contact/static/src/scss/*",
            "geodata_contact/static/src/js/*",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": False,
    "images": [
        "static/description/icon.png",
    ],
}
