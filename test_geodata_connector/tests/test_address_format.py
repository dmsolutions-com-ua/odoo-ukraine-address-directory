from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestAddressFormat(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.CredentialModel = cls.env["geodata.api.credential"]
        cls.AddressModel = cls.env["geodata.address"]

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
                "name": "Test Format Credential",
                "api_connector_id": connector.id,
                "api_username": "test@test.com",
                "api_password": "test_pass",
                "access_token": "test_token_mock",
            }
        )

        cls.address = cls.AddressModel.create(
            {
                "region": "Київська обл.",
                "area": "Броварський р-н",
                "area_old": "Баштанський р-н",
                "hromada": "Броварська",
                "settlement_type": "місто",
                "city": "Бровари",
                "city_old": "Броварі",
                "str_type": "вул.",
                "street": "Київська",
                "street_old": "Леніна",
                "str_type_old": "вул.",
                "house_num": "1",
                "house_num_add": "А",
                "post_index": "07404",
                "apartment_type": "кв.",
                "apartment": "5",
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

    def _set_format(self, doc_format=False, letter_format=False):
        self.credential.write(
            {
                "address_format_document": doc_format,
                "address_format_letter": letter_format,
            }
        )

    def test_01_validation_valid_placeholders(self):
        self._set_format(
            "{country}, {index}, {region}, {area}, {city}, " "{street}, {house}"
        )
        self.assertTrue(self.credential.address_format_document)

    def test_02_validation_all_placeholders(self):
        self._set_format(
            "{country}, {index}, {region}, {area}, {hromada}, "
            "{city}, {street}, {house}, {apartment}, "
            "{region_old}, {area_old}, {city_old}, {street_old}"
        )
        self.assertTrue(self.credential.address_format_document)

    def test_03_validation_invalid_placeholder(self):
        with self.assertRaises(ValidationError):
            self._set_format("{country}, {invalid_field}")

    def test_04_validation_multiple_invalid(self):
        with self.assertRaises(ValidationError):
            self._set_format("{country}, {foo}, {bar}")

    def test_05_validation_empty_allowed(self):
        self._set_format(False, False)
        self.assertFalse(self.credential.address_format_document)

    def test_06_validation_letter_field(self):
        with self.assertRaises(ValidationError):
            self._set_format(False, "{wrong}")

    def test_10_default_format(self):
        self._set_format(False, False)
        result = self.address._format_full_address("ua")
        self.assertIn("УКРАЇНА", result)
        self.assertIn("07404", result)
        self.assertIn("Київська обл.", result)
        self.assertIn("Броварський р-н", result)
        self.assertIn("вул. Київська", result)
        self.assertIn("1А", result)

    def test_11_default_letter_format(self):
        self._set_format(False, False)
        result = self.address._format_letter_address("ua")
        self.assertNotIn("УКРАЇНА", result)
        self.assertIn("07404", result)
        self.assertIn("вул. Київська", result)

    def test_12_custom_full_format(self):
        self._set_format(
            "{country}, {index}, {region}, {area}, {hromada}, "
            "{city}, {street}, {house}"
        )
        result = self.address._format_full_address("ua")
        self.assertEqual(
            result,
            "УКРАЇНА, 07404, Київська обл., "
            "Броварський р-н, "
            "Броварська громада, "
            "місто Бровари, "
            "вул. Київська, 1А",
        )

    def test_13_minimal_format(self):
        self._set_format("{city}, {street}, {house}")
        result = self.address._format_full_address("ua")
        self.assertEqual(result, "місто Бровари, вул. Київська, 1А")

    def test_14_reversed_format(self):
        self._set_format("{street}, {house}, {city}, {region}, {country}")
        result = self.address._format_full_address("ua")
        self.assertEqual(
            result, "вул. Київська, 1А, " "місто Бровари, " "Київська обл., УКРАЇНА"
        )

    def test_15_pipe_separator(self):
        self._set_format("{country} | {region} | {city} | {street} {house}")
        result = self.address._format_full_address("ua")
        self.assertEqual(
            result, "УКРАЇНА | Київська обл. | " "місто Бровари | " "вул. Київська 1А"
        )

    def test_16_letter_custom(self):
        self._set_format(False, "{index}, {city}, {street}, {house}")
        result = self.address._format_letter_address("ua")
        self.assertEqual(result, "07404, місто Бровари, вул. Київська, 1А")

    def test_17_letter_slash_separator(self):
        self._set_format(False, "{city} / {street} / {house}")
        result = self.address._format_letter_address("ua")
        self.assertEqual(result, "місто Бровари / вул. Київська / 1А")

    def test_20_old_name_placeholders(self):
        self._set_format("{city} {city_old}, {area} {area_old}")
        result = self.address._format_full_address("ua")
        self.assertIn("місто Бровари", result)
        self.assertIn("(Броварі)", result)
        self.assertIn("Броварський р-н", result)
        self.assertIn("(Баштанський р-н)", result)

    def test_21_old_name_empty_skipped(self):
        addr_no_old = self.AddressModel.create(
            {
                "region": "Київська",
                "city": "Київ",
                "settlement_type": "місто",
                "str_type": "вул.",
                "street": "Хрещатик",
                "house_num": "1",
            }
        )
        self._set_format("{city} ({city_old}), {street}")
        result = addr_no_old._format_full_address("ua")
        self.assertIn("місто Київ", result)
        self.assertNotIn("()", result)
        self.assertIn("вул. Хрещатик", result)

    def test_22_apartment_placeholder(self):
        self._set_format("{street}, {house}, {apartment}")
        result = self.address._format_full_address("ua")
        self.assertEqual(result, "вул. Київська, 1А, кв. 5")

    def test_30_empty_field_skipped(self):
        addr_no_index = self.AddressModel.create(
            {
                "city": "Київ",
                "settlement_type": "місто",
                "str_type": "вул.",
                "street": "Хрещатик",
                "house_num": "1",
            }
        )
        self._set_format("{country}, {index}, {city}, {street}, {house}")
        result = addr_no_index._format_full_address("ua")
        self.assertEqual(result, "УКРАЇНА, місто Київ, вул. Хрещатик, 1")

    def test_31_multiple_empty_fields_skipped(self):
        addr_minimal = self.AddressModel.create(
            {
                "city": "Київ",
                "settlement_type": "місто",
            }
        )
        self._set_format(
            "{country}, {index}, {region}, {area}, " "{city}, {street}, {house}"
        )
        result = addr_minimal._format_full_address("ua")
        self.assertEqual(result, "УКРАЇНА, місто Київ")

    def test_40_format_independent_doc_letter(self):
        self._set_format("{country}, {city}", "{index}, {street}, {house}")
        doc = self.address._format_full_address("ua")
        letter = self.address._format_letter_address("ua")
        self.assertEqual(doc, "УКРАЇНА, місто Бровари")
        self.assertEqual(letter, "07404, вул. Київська, 1А")

    def test_41_doc_custom_letter_default(self):
        self._set_format("{city}, {street}", False)
        doc = self.address._format_full_address("ua")
        letter = self.address._format_letter_address("ua")
        self.assertEqual(doc, "місто Бровари, вул. Київська")
        self.assertIn("07404", letter)
        self.assertIn("Київська обл.", letter)
