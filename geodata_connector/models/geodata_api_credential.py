import logging
import re

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class GeodataApiCredential(models.Model):
    _name = "geodata.api.credential"
    _inherit = ["kw.api.credential"]
    _description = "Geodata API Credential"

    _ADDRESS_FORMAT_PLACEHOLDERS = {
        "country",
        "index",
        "region",
        "area",
        "hromada",
        "city",
        "street",
        "house",
        "apartment",
        "region_old",
        "area_old",
        "city_old",
        "street_old",
    }

    api_connector_id = fields.Many2one(
        comodel_name="geodata.api.connector",
        required=True,
        help="Geodata API connector configuration",
    )
    api_username = fields.Char(
        string="Username",
        required=True,
        help="Username (email) for Geodata.online service. "
        "Register at https://geodata.online/ to obtain credentials.",
    )
    api_password = fields.Char(
        string="Password",
        required=True,
        help="Password for Geodata.online service authentication.",
    )
    access_token = fields.Char(
        readonly=True,
        help="Current access token obtained from Geodata API. "
        "Automatically refreshed when expired.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        help="Company for which this credential is available. "
        "Leave empty to make it available for all companies.",
    )
    geodata_country_ids = fields.Many2many(
        comodel_name="res.country",
        relation="geodata_credential_country_rel",
        column1="credential_id",
        column2="country_id",
        string="Geodata Countries",
        help="Countries for which Geodata.online provider will be used. "
        "For other countries, default provider will be used.",
    )
    store_english = fields.Boolean(
        string="Store English Translations",
        default=True,
        help="Display English translations for address fields",
    )
    store_russian = fields.Boolean(
        string="Store Russian Translations",
        default=False,
        help="Display Russian translations for address fields",
    )
    default_language = fields.Selection(
        selection=[
            ("uk_UA", "Ukrainian"),
            ("en_US", "English"),
            ("ru_RU", "Russian"),
        ],
        default="uk_UA",
        help="Default language for API requests",
    )
    address_format_document = fields.Char(
        string="Address Format for Documents",
    )
    address_format_letter = fields.Char(
        string="Address Format for Letters",
    )
    payment_notification_interval = fields.Integer(
        string="Payment Alert Interval (minutes)",
        default=60,
        help="Minimum minutes between repeated 'insufficient funds' "
        "notifications to avoid spamming the user. Set to 0 to show every time.",
    )
    payment_notification_last = fields.Datetime(
        string="Last Payment Alert",
        readonly=True,
    )

    @api.constrains("address_format_document", "address_format_letter")
    def _check_address_format(self):
        valid = self._ADDRESS_FORMAT_PLACEHOLDERS
        for record in self:
            for field_name in ("address_format_document", "address_format_letter"):
                template = getattr(record, field_name)
                if not template:
                    continue
                found = re.findall(r"\{(\w+)\}", template)
                invalid = [p for p in found if p not in valid]
                if invalid:
                    raise ValidationError(
                        _(
                            'Invalid placeholders in "%(field)s": '
                            "%(placeholders)s.\n"
                            "Valid placeholders: %(valid)s",
                            field=field_name,
                            placeholders=", ".join(f"{{{p}}}" for p in invalid),
                            valid=", ".join(f"{{{p}}}" for p in sorted(valid)),
                        )
                    )

    def write(self, vals):
        credential_changed = (
            "api_username" in vals or "api_password" in vals
        )
        if credential_changed and "access_token" not in vals:
            vals = dict(vals, access_token=False)
        res = super().write(vals)
        if "address_format_document" in vals or "address_format_letter" in vals:
            addresses = self.env["geodata.address"].search([])
            if addresses:
                addresses._compute_full_addresses()
        return res

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res["api_connector_id"] = self.env.ref(
            "geodata_connector.geodata_api_connector_geodata"
        ).id
        return res

    def get_api_headers_geodata(self, **kwargs):
        if not self.access_token:
            self.action_refresh_api_token()
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }

    _GEODATA_EMPTY_RESULT_MESSAGES = [
        "No cities for this filter.",
        "No streets for this filter or moniker was expired.",
        "No houses for this filter or moniker was expired.",
        "No apartments for this filter or moniker was expired.",
        "Nothing found",
    ]
    _GEODATA_MONIKER_EXPIRED_MESSAGE = "Moniker expired"

    def is_api_success_geodata(self, response, **kwargs):
        if response.status_code == 200:
            return True
        try:
            data = response.json()
        except Exception:
            return False
        message = (data.get("Message") or data.get("message") or "").strip()
        if message in self._GEODATA_EMPTY_RESULT_MESSAGES:
            return True
        return message == self._GEODATA_MONIKER_EXPIRED_MESSAGE

    _PAYMENT_REQUIRED_MESSAGE = _(
        "Insufficient funds on your Geodata.online account. "
        "Please top up your balance at https://geodata.online/"
    )

    def _should_send_payment_notification(self):
        self.ensure_one()
        interval = self.payment_notification_interval or 0
        if interval <= 0:
            return True
        last = self.payment_notification_last
        if not last:
            return True
        elapsed = (fields.Datetime.now() - last).total_seconds() / 60.0
        return elapsed >= interval

    def _send_payment_required_notification(self):
        if self and not self._should_send_payment_notification():
            return
        try:
            self.env["bus.bus"]._sendone(
                self.env.user.partner_id,
                "simple_notification",
                {
                    "type": "danger",
                    "title": _("Geodata.online"),
                    "message": _(
                        "Insufficient funds on your Geodata.online account. "
                        "Please top up your balance at https://geodata.online/"
                    ),
                    "sticky": True,
                },
            )
            if self:
                self.sudo().write(
                    {"payment_notification_last": fields.Datetime.now()}
                )
        except Exception:
            _logger.debug("Failed to send bus notification", exc_info=True)

    def parse_api_error_geodata(self, response, **kwargs):
        if response.status_code == 402:
            _logger.warning(
                "Geodata API: Payment Required (402) for %s",
                response.url if hasattr(response, "url") else "unknown URL",
            )
            self._send_payment_required_notification()
            return {
                "message": str(self._PAYMENT_REQUIRED_MESSAGE),
                "is_payment_required": True,
            }

        try:
            error_data = response.json()
            message = error_data.get("Message") or error_data.get("error")
        except Exception:
            message = None

        if not message:
            reason = (
                response.reason if hasattr(response, "reason") else "No error details"
            )
            message = (
                response.text
                if response.text
                else f"HTTP {response.status_code}: {reason}"
            )

        full_message = f"[{response.status_code}] {message}"
        if hasattr(response, "url") and response.url:
            full_message += f" (URL: {response.url})"

        _logger.error("Geodata API Error: %s", full_message)

        result = {"message": full_message}

        if response.status_code == 401:
            result["is_refresh_api_token_needed"] = True

        return result

    def action_refresh_api_token_geodata(self, **kwargs):
        if not self.api_username or not self.api_password:
            _logger.error("username or password not configured")
            return False

        data = {
            "username": self.api_username,
            "password": self.api_password,
            "grant_type": "password",
        }

        try:
            response = requests.post(
                self.get_api_url("Token"),
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=60,
            )

            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get("access_token")

                if access_token:
                    self.sudo().write({"access_token": access_token})
                    return True

                _logger.error("Token refresh failed: no access_token in response")
                return False

            _logger.error(
                "Token refresh failed with status %s: %s",
                response.status_code,
                response.text,
            )
            return False

        except Exception as e:
            _logger.error("Token refresh error: %s", str(e))
            return False

    @staticmethod
    def _is_payment_required_error(error):
        error_str = str(error)
        return "402" in error_str or "Payment Required" in error_str

    def _get_api_language(self):
        user_lang = self.env.context.get("lang", False)

        lang_map = {
            "uk_UA": "uk_UA",
            "en_US": "en_US",
            "ru_RU": "ru_RU",
        }

        if user_lang and user_lang in lang_map:
            return lang_map[user_lang]

        return self.default_language or "uk_UA"

    def get_geodata_countries(self):
        if self.geodata_country_ids:
            return self.geodata_country_ids
        ukraine = self.env.ref("base.ua", raise_if_not_found=False)
        return ukraine if ukraine else self.env["res.country"]

    def api_address_search(self, sRequest, sLang="uk_UA"):
        self.ensure_one()
        if not sRequest:
            return []

        params = {
            "sRequest": sRequest,
            "sLang": sLang,
        }

        result = self.api_request(
            method="GET",
            url="api/FullAddress",
            params=params,
            silent=False,
        )

        if result and isinstance(result, dict):
            return [result]
        return result if result else []

    def api_cities_search(
        self, sRequest="", sPostCode="", sLang="uk_UA", sRegion=""
    ):
        self.ensure_one()
        if not sRequest and not sPostCode:
            return []
        params = {"sLang": sLang}
        if sPostCode:
            params["sPostCode"] = sPostCode
        else:
            params["sRequest"] = sRequest
        if sRegion:
            params["sRegion"] = sRegion
        return self.api_request(
            method="GET",
            url="api/Cities",
            params=params,
            silent=False,
        )

    @classmethod
    def _is_moniker_expired_result(cls, result):
        if not isinstance(result, dict):
            return False
        msg = (result.get("Message") or result.get("message") or "").strip()
        return msg == cls._GEODATA_MONIKER_EXPIRED_MESSAGE

    @classmethod
    def _normalize_geodata_result(cls, result):
        if isinstance(result, list):
            return result
        if cls._is_moniker_expired_result(result):
            return {"_moniker_expired": True}
        return []

    def api_streets_search(
        self,
        sRequest,
        city_name="",
        city_ref="",
        sLang="uk_UA",
        city_kato="",
        city_koatuu="",
        city_moniker=None,
    ):
        self.ensure_one()
        if not sRequest:
            return []
        moniker = city_moniker or self._resolve_city_moniker(
            city_name,
            city_ref,
            sLang,
            city_kato=city_kato,
            city_koatuu=city_koatuu,
        )
        if not moniker:
            return []
        result = self.api_request(
            method="GET",
            url="api/Streets",
            params={
                "sRequest": sRequest,
                "stMoniker": moniker,
                "sLang": sLang,
            },
            silent=False,
        )
        return self._normalize_geodata_result(result)

    def api_houses_search(
        self,
        sRequest,
        street_name="",
        city_name="",
        city_ref="",
        street_ref="",
        sLang="uk_UA",
        city_kato="",
        city_koatuu="",
        street_moniker=None,
    ):
        self.ensure_one()
        if not sRequest:
            return []
        moniker = street_moniker
        if not moniker:
            if not street_name or not city_name:
                return []
            moniker = self._resolve_street_moniker(
                street_name,
                city_name,
                city_ref,
                street_ref,
                sLang,
                city_kato=city_kato,
                city_koatuu=city_koatuu,
            )
        if not moniker:
            return []
        result = self.api_request(
            method="GET",
            url="api/Houses",
            params={
                "sRequest": sRequest,
                "houseMoniker": moniker,
                "sLang": sLang,
            },
            silent=False,
        )
        return self._normalize_geodata_result(result)

    def api_full_address(self, sRequest, sLang="uk_UA"):
        self.ensure_one()
        if not sRequest:
            return []
        return self.api_request(
            method="GET",
            url="api/FullAddress",
            params={
                "sRequest": sRequest,
                "sLang": sLang,
            },
            silent=True,
        )

    def api_address(self, sRequest, sLang="uk_UA"):
        self.ensure_one()
        if not sRequest:
            return []
        sRequest = " ".join(sRequest.replace(",", " ").split())
        if not sRequest:
            return []
        result = self.api_request(
            method="GET",
            url="api/Address",
            params={
                "sRequest": sRequest,
                "sLang": sLang,
            },
            silent=True,
        )
        if isinstance(result, dict):
            return [result]
        return result if result else []

    def api_user_info(self):
        self.ensure_one()
        result = self.api_request(
            method="GET",
            url="api/Account/UserInfo",
            silent=False,
        )
        if not isinstance(result, dict):
            return {}
        return result

    def action_test_connection(self):
        self.ensure_one()

        if not self.access_token:
            if not self.action_refresh_api_token():
                raise UserError(
                    _(
                        "Failed to obtain access token. "
                        "Please check username and password."
                    )
                )

        try:
            info = self.api_user_info()
            if not info or not info.get("Email"):
                raise UserError(
                    _("API returned empty user info. Please check credentials.")
                )

            _logger.debug("Connection test successful, syncing Ukraine states...")
            from ..tools.ukraine_states_sync import UkraineStatesSync

            try:
                stats = UkraineStatesSync.sync_ukraine_states(self.env)
                _logger.debug(
                    "Ukraine states synced: " "created=%s, updated=%s, skipped=%s",
                    stats["created"],
                    stats["updated"],
                    stats["skipped"],
                )
            except Exception as sync_error:
                _logger.debug("Failed to sync Ukraine states: %s", str(sync_error))

            email = info.get("Email") or ""
            balance = info.get("Balans")
            balance_str = "" if balance is None else "{:.2f}".format(float(balance))
            message = _(
                "Connection successful. Email: %(email)s, Balance: %(balance)s"
            ) % {"email": email, "balance": balance_str}

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Success"),
                    "message": message,
                    "type": "success",
                    "sticky": False,
                },
            }
        except Exception as e:
            if self._is_payment_required_error(e):
                raise UserError(
                    _(
                        "API balance exhausted. Please top up your account "
                        "in the Geodata.online dashboard."
                    )
                ) from e
            if isinstance(e, UserError):
                raise
            raise UserError(_("Connection test failed: %s") % str(e)) from e

    def action_sync_ukraine_states(self):
        """Manually sync Ukraine states from JSON file.

        Can be called from UI button or after successful connection test.
        This method syncs reference data for Ukraine administrative regions
        (oblasts) from JSON file to res.country.state model.

        Returns:
            dict: ir.actions.client notification with sync results
        """
        self.ensure_one()

        from ..tools.ukraine_states_sync import UkraineStatesSync

        try:
            stats = UkraineStatesSync.sync_ukraine_states(self.env)

            if stats.get("error"):
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Error"),
                        "message": _("Failed to sync Ukraine states. Check logs."),
                        "type": "danger",
                        "sticky": True,
                    },
                }

            message = _(
                "Ukraine States Synchronized:\n"
                "• Created: %(created)s\n"
                "• Updated: %(updated)s\n"
                "• Skipped: %(skipped)s"
            ) % {
                "created": stats["created"],
                "updated": stats["updated"],
                "skipped": stats["skipped"],
            }

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Success"),
                    "message": message,
                    "type": "success",
                    "sticky": False,
                },
            }
        except Exception as e:
            _logger.exception("Error syncing Ukraine states: %s", str(e))
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Error"),
                    "message": _("Failed to sync Ukraine states: %s") % str(e),
                    "type": "danger",
                    "sticky": True,
                },
            }

    @api.model
    def get_credential(self, company=None):
        """Get credential for company with fallback to global.

        Search priority:
        1. Active credential for specific company
        2. Active credential without company (global)

        Args:
            company: res.company record or None (use current company)

        Returns:
            geodata.api.credential record or empty recordset
        """
        company = company or self.env.company

        credential = self.search(
            [
                ("company_id", "in", [company.id, False]),
            ],
            limit=1,
            order="company_id DESC NULLS LAST, id DESC",
        )

        if not credential:
            _logger.debug(
                "No active Geodata credential found for company %s", company.name
            )

        return credential

    # === Autocomplete Methods for JS Widget ===

    @api.model
    def autocomplete_full_address(self, query, lang="uk_UA"):
        """Search addresses for autocomplete widget via ORM call."""
        if not query or len(query) < 3:
            return []

        credential = self.get_credential()
        if not credential:
            return []

        try:
            results = credential.api_address(sRequest=query, sLang=lang)
        except Exception as e:
            _logger.debug("Autocomplete API error: %s", str(e))
            return []

        if not isinstance(results, list):
            return []

        suggestions = []
        for data in results:
            if not isinstance(data, dict):
                continue
            address_string = data.get("AddressString")
            if not address_string:
                continue
            suggestions.append(
                {
                    "label": address_string,
                    "value": address_string,
                    "data": data,
                }
            )
        return suggestions

    @staticmethod
    def _normalize_region_name(state_name):
        if not state_name:
            return ""
        text = state_name.strip()
        for suffix in (" область", " обл.", " обл", " oblast"):
            if text.lower().endswith(suffix.lower()):
                return text[: -len(suffix)].strip()
        return text

    @api.model
    def autocomplete_cities(self, query, lang="uk_UA", region=""):
        """Search cities for autocomplete widget via ORM call.

        Returns suggestions with format:
        "{SettlementType} {City} ({CityOld}), {Area}, {Region}"
        Example: "місто Бориспіль, Бориспільський р-н, Київська обл."
        """
        if not query or len(query) < 3:
            return []

        credential = self.get_credential()
        if not credential:
            return []

        try:
            results = credential.api_cities_search(
                sRequest=query, sLang=lang, sRegion=region
            )
        except Exception as e:
            _logger.debug("Autocomplete cities error: %s", str(e))
            return []

        if not isinstance(results, list) or not results:
            return []

        return [self._format_city_suggestion(d) for d in results if isinstance(d, dict)]

    @staticmethod
    def _format_city_suggestion(data):
        if data.get("Id") and not data.get("SettlementId"):
            data["SettlementId"] = data["Id"]
        city_string = data.get("CityString", "")
        return {
            "label": city_string,
            "value": city_string,
            "moniker": data.get("st_moniker", "") or data.get("Moniker", ""),
            "data": data,
        }

    @api.model
    def _strip_settlement_type(self, city_name):
        prefixes = [
            "місто ",
            "село ",
            "селище ",
            "смт ",
            "сmt ",
            "селище міського типу ",
        ]
        lower = city_name.lower()
        for prefix in prefixes:
            if lower.startswith(prefix):
                return city_name[len(prefix) :]
        return city_name

    _STREET_TYPE_PREFIXES = [
        "вул.",
        "вул",
        "вулиця",
        "просп.",
        "просп",
        "проспект",
        "пров.",
        "пров",
        "провулок",
        "бульв.",
        "бульв",
        "бульвар",
        "бул.",
        "бул",
        "б-р",
        "пл.",
        "пл",
        "площа",
        "наб.",
        "наб",
        "набережна",
        "пр.",
        "пр",
        "пр-т",
        "шосе",
        "алея",
        "узвіз",
        "тупик",
    ]

    @api.model
    def _strip_street_type(self, query):
        text = query.strip()
        lower = text.lower()
        for prefix in self._STREET_TYPE_PREFIXES:
            if lower.startswith(prefix + " "):
                return text[len(prefix) :].strip()
        return text

    def _resolve_street_moniker(
        self,
        street_name,
        city_name,
        city_ref="",
        street_ref=False,
        lang="uk_UA",
        city_kato="",
        city_koatuu="",
    ):
        self.ensure_one()
        if not street_name:
            return ""
        results = self.api_streets_search(
            sRequest=street_name,
            city_name=city_name,
            city_ref=city_ref,
            sLang=lang,
            city_kato=city_kato,
            city_koatuu=city_koatuu,
        )
        if not isinstance(results, list) or not results:
            return ""
        street_lower = street_name.lower()
        if street_ref:
            street_ref_lower = str(street_ref).lower()
            for res in results:
                street_val = res.get("Street", "").lower()
                ref = str(res.get("StreetId", "")).lower()
                if street_val == street_lower and ref == street_ref_lower:
                    return res.get("house_moniker", "")
        else:
            for res in results:
                street_val = res.get("Street", "").lower()
                if street_val == street_lower:
                    return res.get("house_moniker", "")
        return results[0].get("house_moniker", "")

    def _resolve_city_moniker(
        self, city_name, city_ref=False, lang="uk_UA", city_kato="", city_koatuu=""
    ):
        self.ensure_one()
        post_code = city_kato or city_koatuu
        if post_code:
            result = self.api_cities_search(sPostCode=post_code, sLang=lang)
            if result and isinstance(result, list) and len(result) == 1:
                moniker = result[0].get("st_moniker", "") or result[0].get(
                    "Moniker", ""
                )
                if moniker:
                    return moniker
        result = self.api_cities_search(sRequest=city_name, sLang=lang)
        if not result:
            return ""
        city_lower = city_name.lower()
        if city_ref:
            city_ref_lower = city_ref.lower()
            for res in result:
                city_val = res.get("City", "").lower()
                ref = str(res.get("Id", "")).lower()
                if city_val == city_lower and ref == city_ref_lower:
                    return res.get("st_moniker", "") or res.get("Moniker", "")
        else:
            for res in result:
                city_val = res.get("City", "").lower()
                if city_val == city_lower:
                    return res.get("st_moniker", "") or res.get("Moniker", "")
        return ""

    def autocomplete_streets(  # pylint: disable=too-many-return-statements
        self,
        query,
        city_name="",
        city_ref="",
        lang="uk_UA",
        city_kato="",
        city_koatuu="",
        city_moniker=None,
    ):
        """Search streets by name within a city.

        Strips street type prefix (вул., просп., etc.) from query,
        calls api_streets_search and formats results as suggestions.
        Returns ``{"_moniker_expired": True}`` so the caller can refresh
        the cached moniker and retry.
        """
        if not query or len(query) < 2:
            return []
        credential = self.get_credential()
        if not credential:
            return []
        if not city_name and not city_moniker:
            return []
        clean_query = self._strip_street_type(query)
        if not clean_query or len(clean_query) < 2:
            return []
        try:
            results = credential.api_streets_search(
                sRequest=clean_query,
                city_name=city_name,
                city_ref=city_ref,
                sLang=lang,
                city_kato=city_kato,
                city_koatuu=city_koatuu,
                city_moniker=city_moniker,
            )
        except Exception as e:
            _logger.debug("Autocomplete streets error: %s", str(e))
            return []
        if isinstance(results, dict) and results.get("_moniker_expired"):
            return results
        if not isinstance(results, list):
            return []
        suggestions = [self._format_street_suggestion(d) for d in results]
        return [s for s in suggestions if s]

    @staticmethod
    def _format_street_suggestion(data):
        if not isinstance(data, dict):
            return None
        street = data.get("Street", "")
        if not street:
            return None
        str_type = data.get("StrType", "") or data.get("StreetType", "")
        street_old = data.get("StreetOld", "")
        house_num = data.get("HouseNum", "")
        house_num_add = data.get("HouseNumAdd", "")
        if house_num and house_num_add:
            house_num = f"{house_num}{house_num_add}"
        city = data.get("City", "")
        settlement_type = data.get("SettlementType", "")
        area = data.get("Area", "")

        street_part = f"{str_type} {street}" if str_type else street
        if street_old and street_old.lower() != street.lower():
            street_part = f"{street_part} ({street_old})"
        if house_num:
            street_part = f"{street_part}, {house_num}"

        label_parts = [street_part]
        if city:
            city_part = f"{settlement_type} {city}" if settlement_type else city
            label_parts.append(city_part)
        if area:
            label_parts.append(area)

        value_part = f"{str_type} {street}" if str_type else street
        if house_num:
            value_part = f"{value_part}, {house_num}"

        return {
            "label": ", ".join(filter(None, label_parts)),
            "value": value_part,
            "data": data,
        }

    @staticmethod
    def _format_house_suggestion(data, query_lower, street_label=""):
        if not isinstance(data, dict):
            return None
        house_num = data.get("HouseNum", "")
        if not house_num:
            return None
        house_add = data.get("HouseNumAdd", "")
        house_full = f"{house_num}{house_add}" if house_add else house_num
        if not house_full.lower().startswith(query_lower):
            return None
        if street_label:
            label = f"{street_label}, {house_full}"
            value = f"{street_label}, {house_num}"
        else:
            label = house_full
            value = house_num
        return {"label": label, "value": value, "data": data}

    @api.model
    def autocomplete_houses(  # pylint: disable=too-many-locals,too-many-return-statements
        self,
        query,
        city_name="",
        city_ref="",
        street_name="",
        street_ref="",
        lang="uk_UA",
        street_label="",
        city_kato="",
        city_koatuu="",
        street_moniker=None,
    ):
        """Search houses by number on a given street.

        Uses ``street_moniker`` (cached) when provided, otherwise resolves
        it via streets search. Returns ``{"_moniker_expired": True}`` so
        the caller can refresh the cached moniker and retry.
        """
        if not query:
            return []
        if not street_moniker and (not city_name or not street_name):
            return []
        credential = self.get_credential()
        if not credential:
            return []
        try:
            results = credential.api_houses_search(
                sRequest=query,
                street_name=street_name,
                city_name=city_name,
                city_ref=city_ref,
                street_ref=street_ref,
                sLang=lang,
                city_kato=city_kato,
                city_koatuu=city_koatuu,
                street_moniker=street_moniker,
            )
        except Exception as e:
            _logger.debug("Autocomplete houses error: %s", str(e))
            return []
        if isinstance(results, dict) and results.get("_moniker_expired"):
            return results
        if not isinstance(results, list) or not results:
            return []
        query_lower = query.lower().strip()
        suggestions = []
        for data in results:
            suggestion = self._format_house_suggestion(data, query_lower, street_label)
            if suggestion:
                suggestions.append(suggestion)
        return suggestions[:15]

    @api.model
    def kw_autocomplete_cities(self, query, dep_values=None):
        credential = self.get_credential(self.env.company)
        if not credential:
            return []
        lang = credential._get_api_language()
        dep = dep_values or {}
        region = ""
        state_val = dep.get("state_id") or dep.get("private_state_id")
        state_id = (
            state_val[0]
            if isinstance(state_val, (list, tuple)) and state_val
            else state_val
        )
        if state_id:
            state = self.env["res.country.state"].sudo().browse(int(state_id))
            if state.exists():
                region = self._normalize_region_name(state.name)
        return credential.autocomplete_cities(query, lang=lang, region=region)

    @staticmethod
    def _build_street_label(geo_addr):
        str_type = geo_addr.str_type or ""
        street = geo_addr.street or ""
        if str_type and street:
            label = f"{str_type} {street}"
        else:
            label = street
        street_old = geo_addr.street_old or ""
        str_type_old = geo_addr.str_type_old or ""
        if street_old and street_old.lower() != street.lower():
            old_part = f"{str_type_old} {street_old}" if str_type_old else street_old
            label = f"{label} ({old_part})"
        return label

    @staticmethod
    def _street_matches_geo_addr(query, geo_addr):
        if not query or not isinstance(query, str):
            return False
        geo_street = (geo_addr.street or "").lower()
        if not geo_street:
            return False
        return geo_street in query.lower()

    @api.model
    def kw_autocomplete_streets(  # pylint: disable=too-many-locals
        self, query, dep_values=None
    ):
        """Entry point for kw_autocomplete JS widget street field.

        Routes to autocomplete_houses() if query contains a house number
        after a known street label, otherwise to autocomplete_streets().
        Reuses ``city_moniker``/``street_moniker`` cached on the linked
        geodata.address; only on a 400 ``Moniker expired`` response we
        re-resolve the moniker once and retry.
        """
        if not query or not isinstance(query, str):
            return []
        credential = self.get_credential(self.env.company)
        if not credential:
            return []
        dep = dep_values or {}
        lang = credential._get_api_language()

        city_name = ""
        city_ref = ""
        city_kato = ""
        city_koatuu = ""
        cached_city_moniker = ""
        cached_street_moniker = ""
        geo_addr = self.env["geodata.address"]
        geo_addr_id = dep.get("geodata_address_id")
        if geo_addr_id:
            geo_addr = self.env["geodata.address"].sudo().browse(int(geo_addr_id))
            if geo_addr.exists():
                city_name = geo_addr.city or ""
                city_ref = str(geo_addr.settlement_ref or "")
                city_kato = geo_addr.kato or ""
                city_koatuu = geo_addr.koatuu or ""
                cached_city_moniker = geo_addr.city_moniker or ""
                cached_street_moniker = geo_addr.street_moniker or ""

        if not city_name:
            return []

        street_label = self._build_street_label(geo_addr)
        if street_label and query.lower().startswith(street_label.lower()):
            remainder = query[len(street_label) :].lstrip(", ").strip()
            if remainder and remainder[0].isdigit():
                return self._run_houses_autocomplete(
                    credential,
                    geo_addr,
                    remainder,
                    city_name=city_name,
                    city_ref=city_ref,
                    street_name=geo_addr.street or "",
                    street_ref=str(geo_addr.street_ref or ""),
                    street_label=street_label,
                    lang=lang,
                    city_kato=city_kato,
                    city_koatuu=city_koatuu,
                    city_moniker=cached_city_moniker,
                    street_moniker=cached_street_moniker,
                )

        return self._run_streets_autocomplete(
            credential,
            geo_addr,
            query,
            city_name=city_name,
            city_ref=city_ref,
            lang=lang,
            city_kato=city_kato,
            city_koatuu=city_koatuu,
            city_moniker=cached_city_moniker,
        )

    def _run_streets_autocomplete(
        self,
        credential,
        geo_addr,
        query,
        city_name,
        city_ref,
        lang,
        city_kato,
        city_koatuu,
        city_moniker,
    ):
        result = credential.autocomplete_streets(
            query,
            city_name=city_name,
            city_ref=city_ref,
            lang=lang,
            city_kato=city_kato,
            city_koatuu=city_koatuu,
            city_moniker=city_moniker,
        )
        if not (isinstance(result, dict) and result.get("_moniker_expired")):
            return result
        fresh = credential._resolve_city_moniker(
            city_name,
            city_ref,
            lang,
            city_kato=city_kato,
            city_koatuu=city_koatuu,
        )
        if not fresh:
            return []
        if geo_addr and geo_addr.exists():
            geo_addr.sudo().write({"city_moniker": fresh})
        retry = credential.autocomplete_streets(
            query,
            city_name=city_name,
            city_ref=city_ref,
            lang=lang,
            city_kato=city_kato,
            city_koatuu=city_koatuu,
            city_moniker=fresh,
        )
        if isinstance(retry, dict):
            return []
        return retry

    def _run_houses_autocomplete(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        credential,
        geo_addr,
        remainder,
        city_name,
        city_ref,
        street_name,
        street_ref,
        street_label,
        lang,
        city_kato,
        city_koatuu,
        city_moniker,
        street_moniker,
    ):
        result = credential.autocomplete_houses(
            remainder,
            city_name=city_name,
            city_ref=city_ref,
            street_name=street_name,
            street_ref=street_ref,
            lang=lang,
            street_label=street_label,
            city_kato=city_kato,
            city_koatuu=city_koatuu,
            street_moniker=street_moniker,
        )
        if not (isinstance(result, dict) and result.get("_moniker_expired")):
            return result
        fresh_street = credential._resolve_street_moniker(
            street_name,
            city_name,
            city_ref,
            street_ref,
            lang,
            city_kato=city_kato,
            city_koatuu=city_koatuu,
        )
        if not fresh_street:
            return []
        if geo_addr and geo_addr.exists():
            geo_addr.sudo().write({"street_moniker": fresh_street})
        retry = credential.autocomplete_houses(
            remainder,
            city_name=city_name,
            city_ref=city_ref,
            street_name=street_name,
            street_ref=street_ref,
            lang=lang,
            street_label=street_label,
            city_kato=city_kato,
            city_koatuu=city_koatuu,
            street_moniker=fresh_street,
        )
        if isinstance(retry, dict):
            return []
        return retry

    @api.model
    def kw_autocomplete_full_address(self, query, dep_values=None):
        credential = self.get_credential(self.env.company)
        if not credential:
            return []
        lang = credential._get_api_language()
        return credential.autocomplete_full_address(query, lang)
