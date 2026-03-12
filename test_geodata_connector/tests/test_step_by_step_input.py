import json
import logging
import os
from unittest.mock import patch

from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)

MOCK_DATA_FILE = os.path.join(os.path.dirname(__file__), "mock_api_data.json")


def load_mock_data():
    with open(MOCK_DATA_FILE) as f:
        return json.load(f)


class TestStepByStepInput(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mock_data = load_mock_data()
        cls.test_cases = {tc["id"]: tc for tc in cls.mock_data["test_cases"]}

        cls.CredentialModel = cls.env["geodata.api.credential"]

        connector = cls.env["geodata.api.connector"].search([], limit=1)
        if not connector:
            connector = cls.env["geodata.api.connector"].create(
                {
                    "name": "Test Connector",
                    "api_url": "https://test.example.com",
                }
            )

        cls.credential = cls.CredentialModel.create(
            {
                "name": "Test Credential",
                "api_connector_id": connector.id,
                "api_username": "test@test.com",
                "api_password": "test_pass",
                "access_token": "test_token_mock",
            }
        )

    def setUp(self):
        super().setUp()
        self._cred_patch = patch.object(
            type(self.CredentialModel),
            "get_credential",
            return_value=self.credential,
        )
        self._cred_patch.start()

    def tearDown(self):
        self._cred_patch.stop()
        super().tearDown()

    def _get_tc(self, tc_id):
        return self.test_cases[tc_id]

    def _mock_cities(self, tc_id):
        tc = self._get_tc(tc_id)
        return tc["api_responses"]["cities"]

    def _mock_streets(self, tc_id):
        tc = self._get_tc(tc_id)
        return tc["api_responses"]["streets"]

    def _mock_houses(self, tc_id):
        tc = self._get_tc(tc_id)
        return tc["api_responses"]["houses"]

    def _mock_fulladdr(self, tc_id):
        tc = self._get_tc(tc_id)
        return tc["api_responses"]["fulladdress"]

    def _find_city_match(self, cities_data, city_name):
        for item in cities_data:
            if item.get("City", "").lower() == city_name.lower():
                return item
        return cities_data[0] if cities_data else None

    @staticmethod
    def _normalize_apostrophe(text):
        return text.replace("\u2019", "'").replace("\u2018", "'")

    def _step_search_city(self, tc_id):
        tc = self._get_tc(tc_id)
        cities_data = self._mock_cities(tc_id)

        with patch.object(
            type(self.credential), "api_cities_search", return_value=cities_data
        ):
            result = self.CredentialModel.autocomplete_cities(
                tc["city_query"], lang="uk_UA"
            )

        self.assertTrue(
            result, f"Cities search for '{tc['city_query']}' " f"should return results"
        )

        city_match = self._find_city_match(cities_data, tc["expect"]["city"])
        self.assertIsNotNone(city_match)

        expected_type = tc["expect"].get("settlement_type")
        if expected_type:
            self.assertEqual(
                city_match.get("SettlementType"),
                expected_type,
                f"Settlement type mismatch for {tc['city_query']}",
            )

        expected_region = tc["expect"].get("region")
        if expected_region:
            self.assertEqual(
                city_match.get("Region"),
                expected_region,
                f"Region mismatch for {tc['city_query']}",
            )

        for suggestion in result:
            if tc["expect"]["city"].lower() in suggestion["value"].lower():
                label = suggestion["label"]
                city_old = city_match.get("CityOld", "")
                city_name = city_match.get("City", "")
                if city_old and city_old.lower() != city_name.lower():
                    self.assertIn(
                        f"({city_old})",
                        label,
                        "Old name should be in parentheses: %s" % label,
                    )
                break

        return result, city_match

    def _step_apply_city(self, partner, city_match):
        moniker = city_match.get("st_moniker", "") or city_match.get("Moniker", "")
        city_name = city_match.get("City", "")
        settlement_type = city_match.get("SettlementType", "")
        region = city_match.get("Region", "")

        vals = {
            "city": f"{settlement_type} {city_name}" if settlement_type else city_name,
            "geodata_city_moniker": moniker,
            "geodata_address_id": partner.geodata_address_id.id or False,
        }

        ukraine = self.env.ref("base.ua", raise_if_not_found=False)
        if ukraine:
            state = self.env["res.country.state"].search(
                [
                    ("country_id", "=", ukraine.id),
                    ("name", "ilike", region.replace(" обл.", "")),
                ],
                limit=1,
            )
            if state:
                vals["state_id"] = state.id

        partner.with_context(skip_street_clear=True).write(vals)

        self.assertTrue(partner.city, "City should be set after selection")
        self.assertFalse(partner.street, "Street should be empty after city")

        return moniker

    def _step_search_street(self, tc_id, city_name):
        tc = self._get_tc(tc_id)
        streets_data = self._mock_streets(tc_id)

        with patch.object(
            type(self.credential), "api_streets_search", return_value=streets_data
        ):
            result = self.CredentialModel.autocomplete_streets(
                tc["street_query"], city_name=city_name, lang="uk_UA"
            )

        self.assertTrue(
            result,
            f"Streets search for '{tc['street_query']}' " f"should return results",
        )

        expected_street = tc["expect"].get("street")
        expected_old = tc["expect"].get("street_old")
        if expected_street:
            found = False
            for suggestion in result:
                norm_label = self._normalize_apostrophe(suggestion["label"])
                norm_expected = self._normalize_apostrophe(expected_street)
                if norm_expected.lower() in norm_label.lower():
                    found = True
                    if expected_old:
                        self.assertIn(
                            f"({expected_old})",
                            suggestion["label"],
                            "Old street name should be in parentheses",
                        )
                    break
            self.assertTrue(found, f"Expected street '{expected_street}' not found")

        return result

    def _step_apply_street(self, partner, street_data):
        if not street_data:
            return ""

        item = street_data[0] if isinstance(street_data, list) else street_data
        street = item.get("Street", "")
        str_type = item.get("StreetType", "") or item.get("StrType", "")
        moniker = item.get("house_moniker", "")

        street_val = f"{str_type} {street}" if str_type else street
        partner.write(
            {
                "street": street_val,
                "geodata_street_moniker": moniker,
                "geodata_address_id": partner.geodata_address_id.id or False,
            }
        )

        self.assertTrue(partner.street, "Street should be set")
        self.assertTrue(partner.city, "City should still be set")

        return moniker

    def _step_search_houses(self, tc_id, city_name, street_name):
        tc = self._get_tc(tc_id)
        house_query = tc.get("house_query")
        if not house_query:
            return []

        houses_data = self._mock_houses(tc_id)
        if not houses_data:
            return []

        with patch.object(
            type(self.credential), "api_houses_search", return_value=houses_data
        ):
            result = self.CredentialModel.autocomplete_houses(
                house_query, city_name=city_name, street_name=street_name, lang="uk_UA"
            )

        self.assertTrue(
            result, f"Houses search for '{house_query}' " f"should return results"
        )

        expected_house = tc["expect"].get("house_num")
        if expected_house:
            found = False
            for suggestion in result:
                data = suggestion.get("data", {})
                h_num = data.get("HouseNum", "")
                h_add = data.get("HouseNumAdd", "")
                if h_num == expected_house or h_num.startswith(expected_house):
                    found = True
                    label = suggestion["label"]
                    self.assertNotIn(
                        tc["expect"]["city"],
                        label,
                        "House label should NOT contain city name",
                    )
                    if h_add:
                        self.assertIn(
                            f"{h_num}{h_add}",
                            label,
                            f"House+letter should be without space: " f"{h_num}{h_add}",
                        )
                    break
            self.assertTrue(found, f"Expected house '{expected_house}' not found")

        return result

    def _apply_js_vals_to_partner(self, partner, result):
        write_vals = {}
        field_map = {
            "zip": "zip",
            "street": "street",
            "street2": "street2",
            "city": "city",
            "partner_latitude": "partner_latitude",
            "partner_longitude": "partner_longitude",
            "area": "area",
            "hromada": "hromada",
        }
        for js_key, field_name in field_map.items():
            val = result.get(js_key)
            if val:
                write_vals[field_name] = val
        state_val = result.get("state_id")
        if state_val and isinstance(state_val, list):
            write_vals["state_id"] = state_val[0]
        addr_val = result.get("geodata_address_id")
        if addr_val and isinstance(addr_val, list):
            write_vals["geodata_address_id"] = addr_val[0]
        elif addr_val:
            write_vals["geodata_address_id"] = addr_val
        if result.get("geodata_city_moniker"):
            write_vals["geodata_city_moniker"] = result["geodata_city_moniker"]
        if result.get("geodata_street_moniker"):
            write_vals["geodata_street_moniker"] = result["geodata_street_moniker"]
        if write_vals:
            partner.write(write_vals)

    def _step_apply_house(self, partner, tc_id, house_data):
        if not house_data:
            return

        fulladdr = self._mock_fulladdr(tc_id)
        if not fulladdr:
            return

        fa_item = fulladdr[0] if isinstance(fulladdr, list) else fulladdr

        with patch.object(
            type(self.credential),
            "api_full_address",
            return_value=[fa_item] if not isinstance(fulladdr, list) else fulladdr,
        ):
            result = self.env["res.partner"].apply_address_to_partner(
                partner.id, fa_item
            )

        self.assertTrue(result, "apply_address_to_partner should return vals")

        self._apply_js_vals_to_partner(partner, result)
        partner.invalidate_recordset()

        if fa_item.get("Index_8x") or fa_item.get("Index_"):
            idx = fa_item.get("Index_") or fa_item.get("Index_8x")
            if idx:
                self.assertEqual(partner.zip, idx, f"Zip should be {idx}")

        self.assertTrue(
            partner.geodata_address_id,
            "Partner should have geodata_address_id after house selection",
        )

    def _run_full_step_test(self, tc_id):
        tc = self._get_tc(tc_id)
        _logger.debug("=== Step-by-step test: %s ===", tc_id)

        partner = self.env["res.partner"].create(
            {
                "name": f"Test {tc_id}",
            }
        )

        ukraine = self.env.ref("base.ua", raise_if_not_found=False)
        if ukraine:
            partner.write({"country_id": ukraine.id})

        _logger.debug("Step 1: Search city '%s'", tc["city_query"])
        _suggestions, city_match = self._step_search_city(tc_id)

        _logger.debug("Step 2: Apply city '%s'", tc["expect"]["city"])
        self._step_apply_city(partner, city_match)
        city_name = city_match.get("City", "")

        _logger.debug("Step 3: Search street '%s'", tc["street_query"])
        self._step_search_street(tc_id, city_name)

        _logger.debug("Step 4: Apply street")
        streets_data = self._mock_streets(tc_id)
        self._step_apply_street(partner, streets_data)
        street_name = tc["expect"].get("street", "")

        if tc.get("house_query"):
            _logger.debug("Step 5: Search house '%s'", tc["house_query"])
            house_suggestions = self._step_search_houses(tc_id, city_name, street_name)

            _logger.debug("Step 6: Apply house")
            self._step_apply_house(partner, tc_id, house_suggestions)

        _logger.debug("=== DONE: %s ===", tc_id)

    def test_step_kyiv_khreshchatyk(self):
        self._run_full_step_test("kyiv_khreshchatyk_1")

    def test_step_kyiv_lukyanenka_renamed(self):
        self._run_full_step_test("kyiv_lukyanenka_13")

    def test_step_kyiv_bankova(self):
        self._run_full_step_test("kyiv_bankova_11")

    def test_step_kharkiv_sumska(self):
        self._run_full_step_test("kharkiv_sumska_10")

    def test_step_kharkiv_mechanizatoriv(self):
        self._run_full_step_test("kharkiv_mechanizatoriv_1")

    def test_step_odesa_derybasivska(self):
        self._run_full_step_test("odesa_derybasivska_1")

    def test_step_brovary(self):
        self._run_full_step_test("brovary_shevchenko_1")

    def test_step_vyshhorod(self):
        self._run_full_step_test("vyshhorod_shevchenko_1")

    def test_step_berdychiv(self):
        self._run_full_step_test("berdychiv_shevchenko_1")

    def test_step_vasylkiv(self):
        self._run_full_step_test("vasylkiv_shevchenko_1")

    def test_step_myronivka(self):
        self._run_full_step_test("myronivka_shevchenko_1")

    def test_step_yakhny_village(self):
        self._run_full_step_test("yakhny_shevchenko_1")

    def test_step_kalynivka(self):
        self._run_full_step_test("kalynivka_shevchenko_1")

    def test_step_koziivka_village(self):
        self._run_full_step_test("koziivka_shevchenko_1")
