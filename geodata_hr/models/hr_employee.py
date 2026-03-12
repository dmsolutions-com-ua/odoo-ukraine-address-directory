from odoo import api, fields, models


class HrEmployee(models.Model):
    _name = "hr.employee"
    _inherit = ["hr.employee", "geodata.address.mixin"]

    _GEODATA_FIELD_MAP = {
        "street": "private_street",
        "street2": "private_street2",
        "city": "private_city",
        "zip": "private_zip",
        "state_id": "private_state_id",
        "country_id": "private_country_id",
        "area": "private_area",
        "hromada": "private_hromada",
        "latitude": False,
        "longitude": False,
    }

    private_area = fields.Char(
        string="Private District",
        groups="hr.group_hr_user",
    )
    private_hromada = fields.Char(
        groups="hr.group_hr_user",
    )
    private_country_code = fields.Char(
        related="private_country_id.code",
        store=False,
    )

    @api.model
    def _build_geodata_vals(self, geo_address, api_data):
        vals = super()._build_geodata_vals(geo_address, api_data)
        if "private_country_id" in vals:
            country = vals.get("private_country_id")
            country_id = (
                country[0]
                if isinstance(country, list) and country
                else country if isinstance(country, int) else False
            )
            if country_id:
                country_rec = self.env["res.country"].browse(country_id)
                if country_rec.exists():
                    vals["private_country_code"] = country_rec.code
        return vals
