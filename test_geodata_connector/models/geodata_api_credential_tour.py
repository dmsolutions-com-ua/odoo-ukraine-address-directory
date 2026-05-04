from odoo import api, models

MOCK_CITIES_KYIV = [
    {
        "label": "місто Київ, Київ",
        "value": "місто Київ",
        "moniker": "1d3a3d41-8ac2-4220-ae54-db096343eaa5",
        "data": {
            "st_moniker": "1d3a3d41-8ac2-4220-ae54-db096343eaa5",
            "Id": 1,
            "City": "Київ",
            "CityString": "місто Київ",
            "Region": "Київ",
            "Area": None,
            "IsOCentre": True,
            "IsRCentre": False,
            "KOATUU": "8000000000",
            "SettlementType": "місто",
            "PhoneCode": "044",
            "Lat": "50.450412",
            "Long": "30.523487",
            "KATO": "UA80000000000093317",
        },
    },
]

MOCK_STREETS_LUK = [
    {
        "label": "вул. Лук'яненка Левка (Тимошенка Маршала), місто Київ",
        "value": "вул. Лук'яненка Левка",
        "data": {
            "house_moniker": "ef360add-38d8-4d83-940e-76a4901d177a",
            "StreetId": 137212,
            "Street": "Лук'яненка Левка",
            "StreetType": "вул.",
            "StreetTypeOld": "вул.",
            "StreetOld": "Тимошенка Маршала",
            "Description": None,
        },
    },
]


class GeodataApiCredentialTour(models.Model):
    _inherit = "geodata.api.credential"

    def _is_mock_api_enabled(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("geodata.test.mock_api", False)
        )

    @api.model
    def kw_autocomplete_cities(self, query, dep_values=None):
        if self._is_mock_api_enabled():
            if query and "Київ".lower().startswith(query.lower()):
                return MOCK_CITIES_KYIV
            return []
        return super().kw_autocomplete_cities(query, dep_values)

    @api.model
    def kw_autocomplete_streets(self, query, dep_values=None):
        if self._is_mock_api_enabled():
            if query and "Лук".lower() in query.lower():
                return MOCK_STREETS_LUK
            return []
        return super().kw_autocomplete_streets(query, dep_values)
