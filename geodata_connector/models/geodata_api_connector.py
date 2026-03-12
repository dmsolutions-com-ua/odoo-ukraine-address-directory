import logging

from odoo import models

_logger = logging.getLogger(__name__)


class GeodataApiConnector(models.Model):
    _name = "geodata.api.connector"
    _inherit = ["kw.api.connector"]
    _description = "Geodata API Connector"
