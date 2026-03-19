from odoo import api, fields, models


class ResCompany(models.Model):
    _name = "res.company"
    _inherit = ["res.company"]

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
            company = self.browse(record_id)
            if company.exists() and company.partner_id:
                partner_id = company.partner_id.id
        result = self.env["res.partner"].apply_address_to_partner(partner_id, api_data)
        result.pop("partner_latitude", None)
        result.pop("partner_longitude", None)
        return result
