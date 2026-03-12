from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestGeodataAutocompleteTour(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        connector = cls.env.ref("geodata_connector.geodata_api_connector_geodata")
        log_source = cls.env.ref("geodata_connector.kw_http_request_log_source_geodata")
        cls.env["geodata.api.credential"].create(
            {
                "name": "Tour Test Credential",
                "active": True,
                "api_connector_id": connector.id,
                "api_username": "tour@test.com",
                "api_password": "tour_password",
                "access_token": "fake_token_for_tour",
                "store_english": False,
                "store_russian": False,
                "kw_http_request_log_source_id": log_source.id,
            }
        )
        cls.env["ir.config_parameter"].sudo().set_param("geodata.test.mock_api", "1")

    def test_geodata_autocomplete_tour(self):
        self.start_tour(
            "/odoo/contacts/new",
            "geodata_autocomplete_city_street_tour",
            login="admin",
            step_delay=200,
        )
