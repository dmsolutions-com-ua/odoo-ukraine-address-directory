from odoo import fields, models


class CrmLead(models.Model):
    _name = "crm.lead"
    _inherit = ["crm.lead", "geodata.address.mixin"]

    country_code = fields.Char(
        related="country_id.code",
        store=False,
    )
    area = fields.Char(
        string="District/Raion",
        translate=True,
    )
    hromada = fields.Char(
        string="Territorial Community",
        translate=True,
    )
