import logging

from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


class TestAddressHierarchy(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ukraine = cls.env.ref("base.ua", raise_if_not_found=False)

    def _create_partner_with_address(self):
        address = self.env["geodata.address"].create(
            {
                "geodata_id": 99990,
                "city": "Київ",
                "street": "Хрещатик",
                "str_type": "вул.",
                "house_num": "1",
                "post_index": "01001",
                "region": "Київ",
                "settlement_type": "місто",
                "city_moniker": "test-moniker-123",
                "street_moniker": "test-street-moniker-456",
            }
        )
        partner = (
            self.env["res.partner"]
            .with_context(
                geodata_applying=True,
            )
            .create(
                {
                    "name": "Hierarchy Test Partner",
                    "country_id": self.ukraine.id if self.ukraine else False,
                    "city": "місто Київ",
                    "street": "вул. Хрещатик, 1",
                    "zip": "01001",
                    "geodata_address_id": address.id,
                }
            )
        )
        return partner.with_context(geodata_applying=False)

    def test_default_country_ukraine(self):
        defaults = self.env["res.partner"].default_get(
            ["country_id", "has_geodata_credential"]
        )

        if self.ukraine:
            self.assertEqual(
                defaults.get("country_id"),
                self.ukraine.id,
                "Default country should be Ukraine",
            )

    def test_change_city_clears_street(self):
        partner = self._create_partner_with_address()

        self.assertTrue(partner.street)

        partner.city = "місто Харків"
        partner._onchange_city_clear_street()

        self.assertFalse(partner.street, "Street should be cleared when city changes")

    def test_change_state_clears_lower_levels(self):
        partner = self._create_partner_with_address()
        partner.area = "Оболонський"
        partner.hromada = "Київська"

        kyiv_state = self.env["res.country.state"].search(
            [
                ("country_id", "=", self.ukraine.id),
                ("name", "ilike", "Харків"),
            ],
            limit=1,
        )

        if kyiv_state:
            partner.state_id = kyiv_state
            partner._onchange_state_clear_lower()

            self.assertFalse(partner.area, "Area should be cleared when state changes")
            self.assertFalse(
                partner.hromada, "Hromada should be cleared when state changes"
            )
            self.assertFalse(partner.city, "City should be cleared when state changes")
            self.assertFalse(
                partner.street, "Street should be cleared when state changes"
            )

    def test_manual_edit_clears_geodata_source(self):
        partner = self._create_partner_with_address()
        address = partner.geodata_address_id

        self.assertTrue(address)
        self.assertTrue(address.geodata_id)

        partner.write({"street": "вул. Інша, 5"})
        address.invalidate_recordset()

        self.assertFalse(
            partner.geodata_address_id,
            "Geodata binding should be cleared on manual edit",
        )
        self.assertFalse(
            address.geodata_id, "Geodata API source should be cleared on manual edit"
        )
        self.assertFalse(
            address.source_query, "Source query should be cleared on manual edit"
        )

    def test_manual_edit_city_clears_geodata_source(self):
        partner = self._create_partner_with_address()
        address = partner.geodata_address_id

        self.assertTrue(address)
        self.assertTrue(address.geodata_id)

        partner.write({"city": "місто Львів"})
        address.invalidate_recordset()

        self.assertFalse(
            partner.geodata_address_id,
            "Geodata binding should be cleared on manual city edit",
        )
        self.assertFalse(
            address.geodata_id,
            "Geodata API source should be cleared on manual city edit",
        )

    def test_manual_edit_zip_clears_geodata_source(self):
        partner = self._create_partner_with_address()
        address = partner.geodata_address_id

        self.assertTrue(address)
        self.assertTrue(address.geodata_id)

        partner.write({"zip": "99999"})
        address.invalidate_recordset()

        self.assertFalse(
            partner.geodata_address_id,
            "Geodata binding should be cleared on manual zip edit",
        )
        self.assertFalse(
            address.geodata_id,
            "Geodata API source should be cleared on manual zip edit",
        )

    def test_geodata_write_preserves_link(self):
        partner = self._create_partner_with_address()
        address = partner.geodata_address_id

        partner.write(
            {
                "street": "вул. Нова, 10",
                "geodata_address_id": address.id,
            }
        )

        self.assertEqual(
            partner.geodata_address_id,
            address,
            "Geodata link should be preserved when explicitly set",
        )

    def test_area_change_clears_hromada(self):
        partner = self._create_partner_with_address()
        partner.area = "Обухівський р-н"
        partner.hromada = "Обухівська"

        partner.area = "Бориспільський р-н"
        partner._onchange_area_clear_lower()

        self.assertFalse(partner.hromada, "Hromada should be cleared when area changes")
