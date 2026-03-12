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


class TestAddressScenarios(TransactionCase):

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

    def _create_partner(self, name):
        ukraine = self.env.ref("base.ua", raise_if_not_found=False)
        vals = {"name": name}
        if ukraine:
            vals["country_id"] = ukraine.id
        return self.env["res.partner"].create(vals)

    def _test_cities_search(self, tc_id):
        tc = self._get_tc(tc_id)
        cities_data = tc["api_responses"]["cities"]

        with patch.object(
            type(self.credential), "api_cities_search", return_value=cities_data
        ):
            result = self.CredentialModel.autocomplete_cities(
                tc["city_query"], lang="uk_UA"
            )

        self.assertTrue(result, f"No cities for '{tc['city_query']}'")

        expected = tc["expect"]
        for item in cities_data:
            if item.get("City", "").lower() == expected["city"].lower():
                if "settlement_type" in expected:
                    self.assertEqual(
                        item["SettlementType"], expected["settlement_type"]
                    )
                if "region" in expected:
                    self.assertEqual(item["Region"], expected["region"])
                if "area" in expected:
                    self.assertEqual(item.get("Area"), expected["area"])
                break

        return result

    def _test_streets_search(self, tc_id, city_name):
        tc = self._get_tc(tc_id)
        streets_data = tc["api_responses"]["streets"]

        with patch.object(
            type(self.credential), "api_streets_search", return_value=streets_data
        ):
            result = self.CredentialModel.autocomplete_streets(
                tc["street_query"], city_name=city_name, lang="uk_UA"
            )

        self.assertTrue(result, f"No streets for '{tc['street_query']}'")

        expected = tc["expect"]
        if "street" in expected:
            labels = [s["label"] for s in result]
            found = any(expected["street"].lower() in lb.lower() for lb in labels)
            self.assertTrue(found, f"Street '{expected['street']}' not in {labels}")

        if "str_type" in expected:
            labels = [s["label"] for s in result]
            found = any(expected["str_type"] in lb for lb in labels)
            self.assertTrue(
                found, f"Street type '{expected['str_type']}' not in {labels}"
            )

        if "street_old" in expected:
            for s in result:
                if expected["street"].lower() in s["label"].lower():
                    self.assertIn(
                        f"({expected['street_old']})",
                        s["label"],
                        f"Old name not in parentheses: {s['label']}",
                    )
                    break

        return result

    def _test_houses_search(self, tc_id, city_name, street_name):
        tc = self._get_tc(tc_id)
        if not tc.get("house_query"):
            return []

        houses_data = tc["api_responses"]["houses"]
        if not houses_data:
            return []

        with patch.object(
            type(self.credential), "api_houses_search", return_value=houses_data
        ):
            result = self.CredentialModel.autocomplete_houses(
                tc["house_query"],
                city_name=city_name,
                street_name=street_name,
                lang="uk_UA",
            )

        self.assertTrue(result, f"No houses for '{tc['house_query']}'")

        for s in result:
            label = s["label"]
            self.assertNotIn(
                tc["expect"]["city"],
                label,
                f"City should not be in house label: {label}",
            )

            data = s.get("data", {})
            h_add = data.get("HouseNumAdd", "")
            h_num = data.get("HouseNum", "")
            if h_add and h_add.strip():
                combined = f"{h_num}{h_add.strip()}"
                self.assertIn(
                    combined,
                    label,
                    f"House+letter without space: {combined} not in {label}",
                )

        return result

    @staticmethod
    def _apply_js_vals_to_partner(partner, result):
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

    def _test_apply_to_partner(self, tc_id):
        tc = self._get_tc(tc_id)
        fulladdr = tc["api_responses"].get("fulladdress", [])
        if not fulladdr:
            return None

        fa_item = fulladdr[0] if isinstance(fulladdr, list) else fulladdr

        if not fa_item.get("City") and not fa_item.get("Street"):
            return None

        partner = self._create_partner(f"Scenario {tc_id}")

        with patch.object(
            type(self.credential),
            "api_full_address",
            return_value=[fa_item] if not isinstance(fulladdr, list) else fulladdr,
        ):
            result = self.env["res.partner"].apply_address_to_partner(
                partner.id, fa_item
            )

        if result:
            self._apply_js_vals_to_partner(partner, result)

        partner.invalidate_recordset()

        self.assertTrue(
            partner.geodata_address_id,
            f"Partner should have geodata_address_id for {tc_id}",
        )

        expected = tc["expect"]
        addr = partner.geodata_address_id

        if "city" in expected:
            self.assertEqual(addr.city, expected["city"])

        if "street" in expected:
            self.assertEqual(addr.street, expected["street"])

        if "house_num" in expected:
            self.assertEqual(addr.house_num, expected["house_num"])

        if "region" in expected:
            self.assertEqual(addr.region, expected["region"])

        idx = fa_item.get("Index_") or fa_item.get("Index_8x")
        if idx:
            self.assertEqual(partner.zip, idx)

        lat = fa_item.get("Lat") or fa_item.get("Lat_")
        if lat:
            self.assertTrue(addr.latitude, f"Latitude should be set for {tc_id}")

        return partner

    def _run_scenario(self, tc_id):
        tc = self._get_tc(tc_id)
        _logger.debug("=== Scenario: %s ===", tc_id)

        cities = tc["api_responses"]["cities"]
        city_match = None
        for item in cities:
            if item.get("City", "").lower() == tc["expect"]["city"].lower():
                city_match = item
                break
        if not city_match and cities:
            city_match = cities[0]

        city_name = city_match.get("City", "") if city_match else ""

        self._test_cities_search(tc_id)

        streets_data = tc["api_responses"]["streets"]
        street_name = ""
        if streets_data:
            self._test_streets_search(tc_id, city_name)
            street_name = streets_data[0].get("Street", "")

        if tc.get("house_query") and street_name:
            self._test_houses_search(tc_id, city_name, street_name)

        self._test_apply_to_partner(tc_id)

        _logger.debug("=== DONE: %s ===", tc_id)

    def test_kyiv_lukyanenka_renamed_street(self):
        self._run_scenario("kyiv_lukyanenka_13")

    def test_kyiv_shevchenko_boulevard(self):
        self._run_scenario("kyiv_shevchenko")

    def test_kyiv_khreshchatyk_basic(self):
        self._run_scenario("kyiv_khreshchatyk_1")

    def test_kyiv_bankova(self):
        self._run_scenario("kyiv_bankova_11")

    def test_kharkiv_sumska(self):
        self._run_scenario("kharkiv_sumska_10")

    def test_kharkiv_mechanizatoriv_letter_in_house(self):
        self._run_scenario("kharkiv_mechanizatoriv_1")

    def test_odesa_derybasivska(self):
        self._run_scenario("odesa_derybasivska_1")

    def test_brovary_full_flow(self):
        self._run_scenario("brovary_shevchenko_1")

    def test_vyshhorod_full_flow(self):
        self._run_scenario("vyshhorod_shevchenko_1")

    def test_berdychiv_full_flow(self):
        self._run_scenario("berdychiv_shevchenko_1")

    def test_vasylkiv_full_flow(self):
        self._run_scenario("vasylkiv_shevchenko_1")

    def test_myronivka_full_flow(self):
        self._run_scenario("myronivka_shevchenko_1")

    def test_yakhny_village(self):
        self._run_scenario("yakhny_shevchenko_1")

    def test_kalynivka_ambiguous(self):
        tc = self._get_tc("kalynivka_shevchenko_1")
        cities_data = tc["api_responses"]["cities"]
        self.assertGreater(
            len(cities_data), 10, "Калинівка should have many results (ambiguous name)"
        )
        self._run_scenario("kalynivka_shevchenko_1")

    def test_koziivka_village(self):
        self._run_scenario("koziivka_shevchenko_1")
