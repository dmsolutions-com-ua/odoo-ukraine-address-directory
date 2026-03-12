from odoo import api, fields, models


class LunchSupplier(models.Model):
    _name = "lunch.supplier"
    _inherit = ["lunch.supplier"]

    geodata_address_id = fields.Many2one(
        related="partner_id.geodata_address_id",
        readonly=False,
        store=False,
    )
    geodata_autocomplete_active = fields.Boolean(
        related="partner_id.geodata_autocomplete_active",
        readonly=False,
        store=False,
    )
    geodata_city_moniker = fields.Char(
        related="partner_id.geodata_city_moniker",
        readonly=False,
        store=False,
    )
    geodata_street_moniker = fields.Char(
        related="partner_id.geodata_street_moniker",
        readonly=False,
        store=False,
    )
    has_geodata_credential = fields.Boolean(
        related="partner_id.has_geodata_credential",
        store=False,
    )
    country_code = fields.Char(
        related="country_id.code",
        store=False,
    )
    area = fields.Char(
        related="partner_id.area",
        readonly=False,
    )
    hromada = fields.Char(
        related="partner_id.hromada",
        readonly=False,
    )

    @api.model
    def apply_geodata_address(self, record_id, api_data):
        if not api_data:
            return {}
        partner_id = False
        if record_id:
            supplier = self.browse(record_id)
            if supplier.exists() and supplier.partner_id:
                partner_id = supplier.partner_id.id
        result = self.env["res.partner"].apply_address_to_partner(partner_id, api_data)
        if "zip" in result:
            result["zip_code"] = result.pop("zip")
        result.pop("partner_latitude", None)
        result.pop("partner_longitude", None)
        return result
