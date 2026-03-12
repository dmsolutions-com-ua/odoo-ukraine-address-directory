import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

try:
    from requests.exceptions import (
        ConnectionError as RequestConnectionError,
        Timeout as RequestTimeout,
    )
except ImportError:

    class RequestTimeout(Exception):
        pass

    class RequestConnectionError(Exception):
        pass


_logger = logging.getLogger(__name__)


class GeodataAddressWizard(models.TransientModel):
    _name = "geodata.address.wizard"
    _description = "Geodata Address Selection Wizard"

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        readonly=True,
        help="Partner record to update with selected address",
    )
    credential_id = fields.Many2one(
        comodel_name="geodata.api.credential",
        string="API Credential",
        required=True,
        domain=[("active", "=", True)],
        help="Select API credential for Geodata service",
    )
    search_query = fields.Char(
        string="Search Address",
        required=True,
        help="Enter city, street, house number to search",
    )
    search_language = fields.Selection(
        selection=[
            ("uk_UA", "Ukrainian"),
            ("en_US", "English"),
            ("ru_RU", "Russian"),
        ],
        default="uk_UA",
        required=True,
        help="Language for API requests and results",
    )
    address_result_ids = fields.One2many(
        comodel_name="geodata.address.wizard.result",
        inverse_name="wizard_id",
        string="Search Results",
        help="Found addresses from Geodata API",
    )
    selected_address_id = fields.Many2one(
        comodel_name="geodata.address",
        string="Selected Address",
        help="Address selected to apply to partner",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        active_model = self.env.context.get("active_model")
        active_id = self.env.context.get("active_id")

        if active_model == "res.partner" and active_id:
            partner = self.env["res.partner"].sudo().browse(active_id)
            res["partner_id"] = partner.id

            search_parts = []
            if partner.city:
                search_parts.append(partner.city)
            if partner.street:
                search_parts.append(partner.street)
            if search_parts:
                res["search_query"] = ", ".join(search_parts)

        credential = self.env["geodata.api.credential"].sudo().search([], limit=1)
        if credential:
            res["credential_id"] = credential.id

        if "search_language" in fields_list:
            default_lang = credential.default_language if credential else "uk_UA"
            res["search_language"] = default_lang

        return res

    def _normalize_search_query(self, query):
        if not query:
            return ""

        query = " ".join(query.split())

        query = re.sub(r"\s*,\s*", ", ", query)
        query = re.sub(r"\s*-\s*", "-", query)

        abbreviations = {
            r"\bвул\.?\s*": "вул. ",
            r"\bпр\.?\s*": "пр. ",
            r"\bпросп\.?\s*": "просп. ",
            r"\bбул\.?\s*": "бул. ",
            r"\bпров\.?\s*": "пров. ",
            r"\bпл\.?\s*": "пл. ",
            r"\bм\.?\s+": "м. ",
            r"\bс\.?\s+": "с. ",
            r"\bсмт\.?\s*": "смт ",
            r"\bобл\.?\s*": "обл. ",
            r"\bр-н\.?\s*": "р-н ",
        }

        for pattern, replacement in abbreviations.items():
            query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)

        return query.strip()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if (
                record.search_query
                and record.credential_id
                and self.env.context.get("auto_search", True)
            ):
                try:
                    record.action_search()
                except (UserError, RequestTimeout, RequestConnectionError) as e:
                    _logger.debug("Auto-search failed for wizard %s: %s", record.id, e)
        return records

    def action_search(self):
        self.ensure_one()

        if not self.search_query:
            raise UserError(_("Please enter search query"))

        if not self.credential_id:
            raise UserError(_("Please select API credential"))

        normalized_query = self._normalize_search_query(self.search_query)

        try:
            api_results = self.credential_id.api_address_search(
                sRequest=normalized_query,
                sLang=self.search_language,
            )
        except RequestTimeout as err:
            raise UserError(_("Request timeout. Please try again later.")) from err
        except RequestConnectionError as err:
            raise UserError(
                _("Cannot connect to Geodata API. " "Check your internet connection.")
            ) from err
        except UserError:
            raise
        except Exception as e:
            _logger.exception("Unexpected error in Geodata API search")
            raise UserError(
                _("Address search failed. Please contact administrator.\n" "Error: %s")
                % str(e)[:100]
            ) from e

        if not api_results:
            raise UserError(_("No addresses found for query: %s") % normalized_query)

        self.address_result_ids.unlink()

        result_records = []
        for api_data in api_results:
            domain = [("house_ref", "=", api_data.get("HouseId"))]

            if api_data.get("Apartment"):
                domain.append(("apartment", "=", api_data.get("Apartment")))

            geodata_address = self.env["geodata.address"].search(domain, limit=1)

            if not geodata_address:
                geodata_address = self.env["geodata.address"].create_from_api_response(
                    api_data
                )

            result_records.append(
                (
                    0,
                    0,
                    {
                        "geodata_address_id": geodata_address.id,
                    },
                )
            )

        self.write({"address_result_ids": result_records})

        return {
            "type": "ir.actions.act_window",
            "res_model": "geodata.address.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _apply_geodata_address_to_partner(self, partner, geodata_address):
        if not geodata_address:
            return False

        geo = partner._ensure_geodata_address()
        geo.update_from_geodata_address(geodata_address)

        partner_vals = geo.to_partner_values()
        partner_vals["date_localization"] = fields.Date.context_today(self)
        partner_vals["geodata_address_id"] = geo.id

        partner.with_context(geodata_applying=True).write(partner_vals)
        return True

    def action_select_and_apply(self):
        self.ensure_one()

        if not self.selected_address_id:
            raise UserError(_("Please select an address from results"))

        if not self.partner_id:
            raise UserError(_("Partner is not specified"))

        self._apply_geodata_address_to_partner(
            self.partner_id, self.selected_address_id
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Success"),
                "message": _("Address has been applied to partner"),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }


class GeodataAddressWizardResult(models.TransientModel):
    _name = "geodata.address.wizard.result"
    _description = "Geodata Address Wizard Result"
    _order = "id"

    wizard_id = fields.Many2one(
        comodel_name="geodata.address.wizard",
        string="Wizard",
        required=True,
        ondelete="cascade",
    )
    geodata_address_id = fields.Many2one(
        comodel_name="geodata.address",
        string="Geodata Address",
        required=True,
    )
    display_address = fields.Char(
        string="Address",
        related="geodata_address_id.address_string",
        readonly=True,
    )
    city = fields.Char(
        string="City",
        related="geodata_address_id.city",
        readonly=True,
    )
    region = fields.Char(
        string="Region",
        related="geodata_address_id.region",
        readonly=True,
    )

    def action_select(self):
        self.ensure_one()
        self.wizard_id.write(
            {
                "selected_address_id": self.geodata_address_id.id,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "geodata.address.wizard",
            "res_id": self.wizard_id.id,
            "view_mode": "form",
            "target": "new",
        }
