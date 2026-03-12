import logging

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


class TestGeodataIntegration(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.credential = cls.env["geodata.api.credential"].search(
            [("active", "=", True)], limit=1
        )

        if not cls.credential:
            _logger.debug(
                "No active geodata.api.credential found in database. "
                "Tests will be skipped."
            )

        cls.test_partner = cls.env["res.partner"].create(
            {
                "name": "Test Partner for Geodata",
                "city": "Київ",
                "street": "Хрещатик",
            }
        )

        cls.sample_api_response = None

    def setUp(self):
        super().setUp()
        if not self.credential:
            self.skipTest("No active credential available")

    def test_01_credential_exists(self):
        self.assertTrue(
            self.credential, "Active geodata.api.credential should exist in database"
        )
        self.assertTrue(self.credential.api_key, "Credential should have api_key")
        self.assertTrue(
            self.credential.api_connector_id, "Credential should have api_connector_id"
        )

    def test_02_api_cities_search(self):
        _logger.debug("Testing api_cities_search with query: Київ")
        try:
            result = self.credential.api_cities_search(sRequest="Київ", sLang="uk_UA")
            self.assertTrue(result, "Cities search should return results")
            self.assertIsInstance(result, list, "Result should be a list")
            if result:
                _logger.debug(f"Found {len(result)} cities")
                self.assertIn("Id", result[0], "Result should contain Id")
                self.assertIn("City", result[0], "Result should contain City")
                self.__class__.sample_api_response = result[0]
        except Exception as e:
            self.fail(f"API cities search failed: {e}")

    def test_03_api_streets_search(self):
        if not self.sample_api_response:
            self.skipTest("No sample API response from previous test")

        city_name = self.sample_api_response.get("City", "Київ")
        self.assertTrue(city_name, "City name should be available")

        _logger.debug(f"Testing api_streets_search with city_name: " f"{city_name}")
        try:
            result = self.credential.api_streets_search(
                sRequest="Хрещатик", city_name=city_name, sLang="uk_UA"
            )
            self.assertIsInstance(result, list, "Result should be a list")
            if result:
                _logger.debug(f"Found {len(result)} streets")
        except Exception as e:
            self.fail(f"API streets search failed: {e}")

    def test_04_api_address_search(self):
        _logger.debug("Testing api_address_search with full address")
        try:
            result = self.credential.api_address_search(
                sRequest="Київ, Хрещатик 1", sLang="uk_UA"
            )
            self.assertIsInstance(result, list, "Result should be a list")
            if result:
                _logger.debug(f"Found {len(result)} addresses")
                self.assertIn(
                    "AddressString", result[0], "Result should contain AddressString"
                )
        except Exception as e:
            self.fail(f"API address search failed: {e}")

    def test_05_create_from_api_response(self):
        if not self.sample_api_response:
            self.skipTest("No sample API response from previous test")

        _logger.debug("Testing create_from_api_response")
        address = self.env["geodata.address"].create_from_api_response(
            self.sample_api_response
        )

        self.assertTrue(address, "Address should be created")
        self.assertTrue(address.id, "Address should have ID")
        self.assertEqual(
            address.geodata_id,
            self.sample_api_response.get("Id"),
            "geodata_id should match API response",
        )

    def test_06_to_partner_values(self):
        if not self.sample_api_response:
            self.skipTest("No sample API response from previous test")

        address = self.env["geodata.address"].create_from_api_response(
            self.sample_api_response
        )
        partner_vals = address.to_partner_values()

        self.assertIsInstance(partner_vals, dict, "Should return dictionary")
        self.assertIn("city", partner_vals, "Should contain city field")

    def test_07_wizard_default_get(self):
        _logger.debug("Testing wizard default_get with partner context")

        wizard = (
            self.env["geodata.address.wizard"]
            .with_context(active_model="res.partner", active_id=self.test_partner.id)
            .create({})
        )

        self.assertEqual(
            wizard.partner_id,
            self.test_partner,
            "Wizard should have partner from context",
        )
        self.assertEqual(
            wizard.credential_id,
            self.credential,
            "Wizard should auto-select credential",
        )
        self.assertTrue(
            wizard.search_query, "Wizard should pre-fill search_query from partner"
        )
        _logger.debug(f"Auto-filled search query: {wizard.search_query}")

    def test_08_wizard_search_empty_query(self):
        _logger.debug("Testing wizard search with empty query")

        wizard = self.env["geodata.address.wizard"].create(
            {
                "partner_id": self.test_partner.id,
                "credential_id": self.credential.id,
                "search_query": "",
            }
        )

        with self.assertRaises(UserError) as cm:
            wizard.action_search()

        self.assertIn(
            "search query",
            str(cm.exception).lower(),
            "Error should mention search query",
        )

    def test_09_wizard_search_no_credential(self):
        _logger.debug("Testing wizard search without credential")

        wizard = self.env["geodata.address.wizard"].create(
            {
                "partner_id": self.test_partner.id,
                "search_query": "Київ",
            }
        )

        with self.assertRaises(UserError) as cm:
            wizard.action_search()

        self.assertIn(
            "credential", str(cm.exception).lower(), "Error should mention credential"
        )

    def test_10_wizard_search_success(self):
        _logger.debug("Testing wizard successful search")

        wizard = self.env["geodata.address.wizard"].create(
            {
                "partner_id": self.test_partner.id,
                "credential_id": self.credential.id,
                "search_query": "Київ, Хрещатик 1",
                "search_language": "uk_UA",
            }
        )

        try:
            result = wizard.action_search()
            self.assertIsInstance(result, dict, "Should return action dict")
            self.assertEqual(
                result.get("res_model"),
                "geodata.address.wizard",
                "Should return to wizard",
            )
        except Exception as e:
            self.fail(f"Wizard search failed: {e}")

    def test_11_wizard_search_creates_results(self):
        _logger.debug("Testing wizard creates result records")

        wizard = self.env["geodata.address.wizard"].create(
            {
                "partner_id": self.test_partner.id,
                "credential_id": self.credential.id,
                "search_query": "Київ, Хрещатик 1",
                "search_language": "uk_UA",
            }
        )

        try:
            wizard.action_search()
            self.assertTrue(
                wizard.address_result_ids, "Wizard should have result records"
            )
            _logger.debug(f"Created {len(wizard.address_result_ids)} result records")

            for result in wizard.address_result_ids:
                self.assertTrue(
                    result.geodata_address_id, "Result should have geodata_address_id"
                )
                self.assertTrue(
                    result.display_address, "Result should have display_address"
                )
        except Exception as e:
            self.fail(f"Failed to create results: {e}")

    def test_12_wizard_select_address(self):
        _logger.debug("Testing wizard address selection")

        wizard = self.env["geodata.address.wizard"].create(
            {
                "partner_id": self.test_partner.id,
                "credential_id": self.credential.id,
                "search_query": "Київ, Хрещатик 1",
            }
        )

        try:
            wizard.action_search()

            if not wizard.address_result_ids:
                self.skipTest("No results to select from")

            first_result = wizard.address_result_ids[0]
            action = first_result.action_select()

            self.assertIsInstance(action, dict, "Should return action")
            self.assertEqual(
                wizard.selected_address_id,
                first_result.geodata_address_id,
                "Selected address should be set",
            )
            _logger.debug(
                f"Selected address: {wizard.selected_address_id.display_name}"
            )
        except Exception as e:
            self.fail(f"Address selection failed: {e}")

    def test_13_wizard_apply_to_partner(self):
        _logger.debug("Testing wizard apply address to partner")

        original_city = self.test_partner.city
        original_street = self.test_partner.street

        wizard = self.env["geodata.address.wizard"].create(
            {
                "partner_id": self.test_partner.id,
                "credential_id": self.credential.id,
                "search_query": "Київ, Хрещатик 1",
            }
        )

        try:
            wizard.action_search()

            if not wizard.address_result_ids:
                self.skipTest("No results to apply")

            wizard.selected_address_id = wizard.address_result_ids[0].geodata_address_id
            result = wizard.action_select_and_apply()

            self.assertIsInstance(result, dict, "Should return notification")
            self.assertEqual(
                self.test_partner.geodata_address_id,
                wizard.selected_address_id,
                "Partner should have geodata_address_id",
            )

            _logger.debug(
                f"Partner address updated from "
                f'"{original_city}, {original_street}" '
                f'to "{self.test_partner.city}, {self.test_partner.street}"'
            )
        except Exception as e:
            self.fail(f"Apply to partner failed: {e}")

    def test_14_wizard_full_flow(self):
        _logger.debug("Testing complete wizard flow")

        test_partner = self.env["res.partner"].create(
            {
                "name": "Full Flow Test Partner",
                "city": "Львів",
            }
        )

        wizard = (
            self.env["geodata.address.wizard"]
            .with_context(active_model="res.partner", active_id=test_partner.id)
            .create({})
        )

        self.assertEqual(wizard.partner_id, test_partner)
        self.assertEqual(wizard.credential_id, self.credential)

        wizard.search_query = "Київ, Хрещатик 1"

        try:
            wizard.action_search()

            self.assertTrue(wizard.address_result_ids, "Should have search results")

            first_result = wizard.address_result_ids[0]
            first_result.action_select()

            self.assertTrue(wizard.selected_address_id, "Address should be selected")

            wizard.action_select_and_apply()

            self.assertTrue(
                test_partner.geodata_address_id, "Partner should have geodata address"
            )
            self.assertTrue(
                test_partner.has_geodata_address, "has_geodata_address should be True"
            )

            _logger.debug(
                f"Full flow completed successfully. "
                f"Partner address: {test_partner.street}, {test_partner.city}"
            )
        except Exception as e:
            self.fail(f"Full flow failed: {e}")

    def test_15_partner_action_open_wizard(self):
        _logger.debug("Testing partner action_open_geodata_wizard")

        action = self.test_partner.action_open_geodata_wizard()

        self.assertIsInstance(action, dict, "Should return action dict")
        self.assertEqual(
            action.get("res_model"), "geodata.address.wizard", "Should open wizard"
        )
        self.assertEqual(action.get("target"), "new", "Should open in dialog")
        self.assertEqual(
            action["context"].get("active_id"),
            self.test_partner.id,
            "Context should have partner id",
        )

    def test_16_partner_apply_geodata_address(self):
        _logger.debug("Testing partner apply_geodata_address method")

        wizard = self.env["geodata.address.wizard"].create(
            {
                "partner_id": self.test_partner.id,
                "credential_id": self.credential.id,
                "search_query": "Київ, Хрещатик 1",
            }
        )

        try:
            wizard.action_search()

            if not wizard.address_result_ids:
                self.skipTest("No results available")

            geodata_address = wizard.address_result_ids[0].geodata_address_id
            result = self.test_partner.apply_geodata_address(geodata_address)

            self.assertTrue(result, "apply_geodata_address should return True")
            self.assertEqual(
                self.test_partner.geodata_address_id,
                geodata_address,
                "Partner should have geodata_address_id",
            )
            _logger.debug("Partner address applied successfully")
        except Exception as e:
            self.fail(f"Apply geodata address failed: {e}")

    def test_17_wizard_search_invalid_query(self):
        _logger.debug("Testing wizard with non-existent address")

        wizard = self.env["geodata.address.wizard"].create(
            {
                "partner_id": self.test_partner.id,
                "credential_id": self.credential.id,
                "search_query": "NONEXISTENTCITY123456789ABCDEF",
            }
        )

        with self.assertRaises(UserError) as cm:
            wizard.action_search()

        error_msg = str(cm.exception).lower()
        self.assertTrue(
            "no addresses found" in error_msg or "not found" in error_msg,
            "Should indicate no addresses found",
        )

    def test_18_wizard_apply_without_selection(self):
        _logger.debug("Testing wizard apply without address selection")

        wizard = self.env["geodata.address.wizard"].create(
            {
                "partner_id": self.test_partner.id,
                "credential_id": self.credential.id,
                "search_query": "Київ",
            }
        )

        with self.assertRaises(UserError) as cm:
            wizard.action_select_and_apply()

        self.assertIn(
            "select", str(cm.exception).lower(), "Error should mention selection"
        )

    def test_19_credential_test_connection(self):
        _logger.debug("Testing credential action_test_connection")

        try:
            result = self.credential.action_test_connection()
            self.assertIsInstance(result, dict, "Should return action dict")
            self.assertEqual(
                result.get("type"), "ir.actions.client", "Should be client action"
            )
            self.assertEqual(
                result["params"].get("type"),
                "success",
                "Should be success notification",
            )
            _logger.debug("Connection test successful")
        except UserError as e:
            self.fail(f"Connection test failed: {e}")


class TestGeodataUnitTests(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_partner = cls.env["res.partner"].create(
            {
                "name": "Test Partner for Unit Tests",
                "city": "Київ",
                "street": "Хрещатик",
            }
        )

    def test_01_apply_address_to_partner_new(self):
        _logger.debug("Testing apply_address_to_partner for new partner")

        api_data = {
            "ID": 12345,
            "AddressString": "м. Київ, вул. Хрещатик, 1",
            "City": "Київ",
            "Street": "Хрещатик",
            "StrType": "вул.",
            "HouseNum": "1",
            "Index_8x": "01001",
            "Region": "Київська область",
            "Lat_": "50.4501",
            "Long_": "30.5234",
        }

        result = self.env["res.partner"].apply_address_to_partner(False, api_data)

        self.assertIsInstance(result, dict)
        self.assertIn("geodata_address_id", result)
        self.assertTrue(result["geodata_address_id"])
        self.assertEqual(result.get("city"), "Київ")
        self.assertIn("partner_latitude", result)
        _logger.debug("apply_address_to_partner for new partner: OK")

    def test_02_apply_address_to_partner_existing(self):
        _logger.debug("Testing apply_address_to_partner for existing partner")

        api_data = {
            "ID": 12346,
            "AddressString": "м. Львів, пл. Ринок, 1",
            "City": "Львів",
            "Street": "Ринок",
            "StrType": "пл.",
            "HouseNum": "1",
            "Index_8x": "79000",
            "Region": "Львівська область",
            "Lat_": "49.8419",
            "Long_": "24.0315",
        }

        result = self.env["res.partner"].apply_address_to_partner(
            self.test_partner.id, api_data
        )

        self.assertIsInstance(result, dict)
        self.assertIn("geodata_address_id", result)

        address_id_value = result["geodata_address_id"]
        address_id = (
            address_id_value[0]
            if isinstance(address_id_value, list)
            else address_id_value
        )
        geodata_address = self.env["geodata.address"].browse(address_id)
        self.assertTrue(geodata_address.exists())
        self.assertEqual(geodata_address.city, "Львів")
        _logger.debug("apply_address_to_partner for existing partner: OK")

    def test_03_apply_address_to_partner_update(self):
        _logger.debug("Testing apply_address_to_partner updates existing")

        first_api_data = {
            "ID": 12347,
            "City": "Харків",
            "Index_8x": "61000",
        }
        partner_model = self.env["res.partner"]
        first_result = partner_model.apply_address_to_partner(
            self.test_partner.id, first_api_data
        )
        first_address_id_value = first_result["geodata_address_id"]
        first_address_id = (
            first_address_id_value[0]
            if isinstance(first_address_id_value, list)
            else first_address_id_value
        )

        self.test_partner.geodata_address_id = first_address_id

        second_api_data = {
            "ID": 12348,
            "City": "Одеса",
            "Index_8x": "65000",
        }
        second_result = partner_model.apply_address_to_partner(
            self.test_partner.id, second_api_data
        )

        second_address_id_value = second_result["geodata_address_id"]
        second_address_id = (
            second_address_id_value[0]
            if isinstance(second_address_id_value, list)
            else second_address_id_value
        )
        self.assertEqual(second_address_id, first_address_id)

        geodata_address = self.env["geodata.address"].browse(first_address_id)
        self.assertEqual(geodata_address.city, "Одеса")
        _logger.debug("apply_address_to_partner update existing: OK")

    def test_04_update_from_api_response(self):
        _logger.debug("Testing geodata.address.update_from_api_response")

        address = self.env["geodata.address"].create(
            {
                "geodata_id": 99999,
                "city": "Old City",
                "post_index": "00000",
            }
        )

        api_data = {
            "ID": 88888,
            "City": "New City",
            "Index_8x": "11111",
            "Lat_": "50.0",
            "Long_": "30.0",
        }
        address.update_from_api_response(api_data)

        self.assertEqual(address.geodata_id, 88888)
        self.assertEqual(address.city, "New City")
        self.assertEqual(address.post_index, "11111")
        self.assertEqual(address.latitude, 50.0)
        _logger.debug("update_from_api_response: OK")
