import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "geodata.address.mixin"]

    _GEODATA_FIELD_MAP = {
        "street": "street",
        "street2": "street2",
        "city": "city",
        "zip": "zip",
        "state_id": "state_id",
        "country_id": "country_id",
        "area": "area",
        "hromada": "hromada",
        "latitude": "partner_latitude",
        "longitude": "partner_longitude",
    }

    geocoding_source = fields.Char(
        compute="_compute_geocoding_source",
        store=True,
    )
    area = fields.Char(
        string="District/Raion",
        translate=True,
    )
    hromada = fields.Char(
        string="Territorial Community",
        translate=True,
    )
    geodata_search = fields.Char(
        string="Address Search",
        compute="_compute_geodata_search",
        inverse="_inverse_geodata_search",
        store=False,
    )
    geodata_address_ua_postal = fields.Char(
        string="Address (UA Postal)",
        related="geodata_address_id.address_ua_postal",
        readonly=True,
    )
    geodata_address_ua_short = fields.Char(
        string="Address (UA Short)",
        related="geodata_address_id.address_ua_short",
        readonly=True,
    )
    geodata_address_western = fields.Char(
        string="Address (Western)",
        related="geodata_address_id.address_western",
        readonly=True,
    )
    geodata_city_en = fields.Char(
        string="City (EN)",
        related="geodata_address_id.city_en",
        readonly=True,
    )
    geodata_street_en = fields.Char(
        string="Street (EN)",
        related="geodata_address_id.street_en",
        readonly=True,
    )
    geodata_area_en = fields.Char(
        string="Area (EN)",
        related="geodata_address_id.area_en",
        readonly=True,
    )
    geodata_hromada_en = fields.Char(
        string="Hromada (EN)",
        related="geodata_address_id.hromada_en",
        readonly=True,
    )
    geodata_city_ru = fields.Char(
        string="City (RU)",
        related="geodata_address_id.city_ru",
        readonly=True,
    )
    geodata_street_ru = fields.Char(
        string="Street (RU)",
        related="geodata_address_id.street_ru",
        readonly=True,
    )
    geodata_area_ru = fields.Char(
        string="Area (RU)",
        related="geodata_address_id.area_ru",
        readonly=True,
    )
    geodata_hromada_ru = fields.Char(
        string="Hromada (RU)",
        related="geodata_address_id.hromada_ru",
        readonly=True,
    )
    geodata_address_full_ua = fields.Char(
        string="Full Address (UA)",
        related="geodata_address_id.address_full_ua",
        readonly=True,
    )
    geodata_address_full_ru = fields.Char(
        string="Full Address (RU)",
        related="geodata_address_id.address_full_ru",
        readonly=True,
    )
    geodata_address_full_en = fields.Char(
        string="Full Address (EN)",
        related="geodata_address_id.address_full_en",
        readonly=True,
    )
    geodata_address_letter_ua = fields.Char(
        string="Letter Address (UA)",
        related="geodata_address_id.address_letter_ua",
        readonly=True,
    )
    geodata_address_letter_ru = fields.Char(
        string="Letter Address (RU)",
        related="geodata_address_id.address_letter_ru",
        readonly=True,
    )
    geodata_address_letter_en = fields.Char(
        string="Letter Address (EN)",
        related="geodata_address_id.address_letter_en",
        readonly=True,
    )
    geodata_kato = fields.Char(
        string="KATOTTG",
        related="geodata_address_id.kato",
        readonly=True,
    )
    geodata_koatuu = fields.Char(
        string="KOATUU",
        related="geodata_address_id.koatuu",
        readonly=True,
    )
    geodata_phone_code = fields.Char(
        string="Phone Code",
        related="geodata_address_id.phone_code",
        readonly=True,
    )
    geodata_terr_status = fields.Char(
        string="Territory Status",
        related="geodata_address_id.terr_status",
        readonly=True,
    )
    geodata_is_regional_center = fields.Boolean(
        string="Regional Center",
        related="geodata_address_id.is_regional_center",
        readonly=True,
    )
    geodata_is_district_center = fields.Boolean(
        string="District Center",
        related="geodata_address_id.is_district_center",
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        credential = self.env["geodata.api.credential"].sudo().get_credential()
        res["has_geodata_credential"] = credential

        if "country_id" in fields_list and "country_id" not in res:
            ukraine = self.env.ref("base.ua", raise_if_not_found=False)
            if ukraine:
                res["country_id"] = ukraine.id

        return res

    def _compute_geodata_search(self):
        for partner in self:
            partner.geodata_search = ""

    def _inverse_geodata_search(self):
        pass

    def _compute_geocoding_source(self):
        for partner in self:
            if hasattr(partner, "geodata_address_id") and partner.geodata_address_id:
                partner.geocoding_source = "geodata"
            elif partner.partner_latitude or partner.partner_longitude:
                partner.geocoding_source = "other"
            else:
                partner.geocoding_source = False

    def _clear_geodata_link(self):
        self.geodata_address_id = False
        self.geodata_city_moniker = False
        self.geodata_street_moniker = False

    @api.onchange("state_id")
    def _onchange_state_clear_lower(self):
        if self.geodata_autocomplete_active:
            return
        if self.country_id and self.country_id.code == "UA":
            self.area = False
            self.hromada = False
            self.city = False
            self.street = False
            self.street2 = False
            self.zip = False

    @api.onchange("country_id")
    def _onchange_country_clear_geodata(self):
        if self.geodata_autocomplete_active:
            return
        self.area = False
        self.hromada = False
        self.city = False
        self.street = False
        self.street2 = False
        self.zip = False
        if not self.country_id or self.country_id.code != "UA":
            self._clear_geodata_link()

    @api.onchange("area")
    def _onchange_area_clear_lower(self):
        if self.geodata_autocomplete_active:
            return
        if self.country_id and self.country_id.code == "UA":
            self.hromada = False
            self.city = False
            self.street = False
            self.street2 = False
            self.zip = False

    @api.onchange("city")
    def _onchange_city_clear_street(self):
        if self.geodata_autocomplete_active:
            return
        if self.country_id and self.country_id.code == "UA":
            self.street = False
            self.street2 = False
            self.zip = False

    @api.onchange("street")
    def _onchange_street_clear_zip(self):
        if self.geodata_autocomplete_active:
            return
        if self.country_id and self.country_id.code == "UA":
            self.street2 = False
            self.zip = False

    def _geo_localize_with_geodata(self, partners):
        provider = self.env["base.geo_provider"].search(
            [("tech_name", "=", "geodata")], limit=1
        )

        if not provider:
            raise UserError(_("Geodata provider not found"))

        config_param = self.env["ir.config_parameter"].sudo()
        old_param = config_param.get_param("base_geolocalize.geo_provider")

        try:
            config_param.set_param("base_geolocalize.geo_provider", provider.id)
            return super(ResPartner, partners).geo_localize()
        finally:
            if old_param is not None:
                config_param.set_param("base_geolocalize.geo_provider", old_param)
            else:
                config_param.set_param("base_geolocalize.geo_provider", False)

    def geo_localize(self):
        credential = self.env["geodata.api.credential"].sudo().get_credential()
        geodata_countries = (
            credential.get_geodata_countries()
            if credential
            else self.env["res.country"]
        )

        partners_for_geodata = self.filtered(
            lambda p: p.country_id and p.country_id in geodata_countries
        )
        partners_for_standard = self - partners_for_geodata

        if partners_for_geodata:
            self._geo_localize_with_geodata(partners_for_geodata)

        if partners_for_standard:
            super(ResPartner, partners_for_standard).geo_localize()

        return True

    _PARTNER_GEO_HOUSE_CLEAR = [
        "house_num",
        "house_num_add",
        "house_ref",
        "apartment_type",
        "apartment",
        "addition_address",
        "apartment_type_en",
        "apartment_type_ru",
        "post_index",
        "latitude",
        "longitude",
    ]

    _PARTNER_GEO_CLEAR_MAP = {
        "street": [
            "street",
            "str_type",
            "street_old",
            "str_type_old",
            "street_moniker",
            "street_ref",
            "street_en",
            "street_ru",
            "str_type_en",
            "str_type_ru",
            "house_num",
            "house_num_add",
            "house_ref",
            "apartment_type",
            "apartment",
            "addition_address",
            "apartment_type_en",
            "apartment_type_ru",
            "post_index",
            "latitude",
            "longitude",
        ],
        "city": [
            "city",
            "settlement_type",
            "city_old",
            "settlement_type_old",
            "city_moniker",
            "settlement_ref",
            "city_en",
            "city_ru",
            "settlement_type_en",
            "settlement_type_ru",
            "city_district",
            "city_district_en",
            "city_district_ru",
            "latitude_settlement",
            "longitude_settlement",
            "koatuu",
            "kato",
            "phone_code",
            "is_regional_center",
            "is_district_center",
            "metro_station",
            "metro_line",
            "metro_distance",
            "terr_status",
        ],
        "state_id": [
            "region",
            "region_old",
            "region_en",
            "region_ru",
        ],
        "area": [
            "area",
            "area_old",
            "area_en",
            "area_ru",
        ],
        "hromada": [
            "hromada",
            "hromada_old",
            "hromada_en",
            "hromada_ru",
        ],
        "zip": [
            "post_index",
        ],
    }

    _PARTNER_FIELD_LEVEL = [
        "country_id",
        "state_id",
        "area",
        "hromada",
        "city",
        "street",
        "zip",
    ]

    def _get_geo_fields_to_clear(self, changed_fields):
        clear_fields = set()
        highest_level = len(self._PARTNER_FIELD_LEVEL)
        for field in changed_fields:
            if field in self._PARTNER_FIELD_LEVEL:
                idx = self._PARTNER_FIELD_LEVEL.index(field)
                if idx < highest_level:
                    highest_level = idx
        for field in self._PARTNER_FIELD_LEVEL[highest_level:]:
            geo_fields = self._PARTNER_GEO_CLEAR_MAP.get(field, [])
            clear_fields.update(geo_fields)
        return clear_fields

    def _classify_address_changes(self, vals):
        address_field_set = set(self._PARTNER_GEO_CLEAR_MAP.keys()) | {"country_id"}
        cleared_fields = set()
        changed_fields = set()
        for f in vals:
            if f not in address_field_set:
                continue
            if not vals[f]:
                cleared_fields.add(f)
            else:
                changed_fields.add(f)
        return cleared_fields, changed_fields

    @staticmethod
    def _is_house_only_change(geo_addr, new_street):
        if not geo_addr or not geo_addr.street:
            return False
        geo_street = geo_addr.street.lower()
        new_lower = (new_street or "").lower()
        return geo_street in new_lower

    def _build_geo_clear_vals(self, geo_addr, fields_to_clear):
        geo_vals = {"geodata_id": False, "source_query": False}
        for field in fields_to_clear:
            if not hasattr(geo_addr, field):
                continue
            current = getattr(geo_addr, field)
            if isinstance(current, (int, float)) and not isinstance(current, bool):
                geo_vals[field] = 0
            else:
                geo_vals[field] = False
        return geo_vals

    def _update_geodata_on_address_change(self, partner, vals):
        geo_addr = partner.geodata_address_id
        if not geo_addr:
            return

        if "country_id" in vals and vals["country_id"]:
            ukraine = self.env.ref("base.ua", raise_if_not_found=False)
            if ukraine and vals["country_id"] != ukraine.id:
                partner.geodata_address_id = False
                return

        cleared_fields, changed_fields = self._classify_address_changes(vals)
        if not cleared_fields and not changed_fields:
            return

        fields_to_clear = set()
        if cleared_fields:
            fields_to_clear.update(self._get_geo_fields_to_clear(cleared_fields))
        for f in changed_fields:
            if f == "street" and self._is_house_only_change(
                geo_addr, vals.get("street", "")
            ):
                fields_to_clear.update(self._PARTNER_GEO_HOUSE_CLEAR)
            else:
                fields_to_clear.update(self._PARTNER_GEO_CLEAR_MAP.get(f, []))

        geo_vals = self._build_geo_clear_vals(geo_addr, fields_to_clear)
        geo_addr.write(geo_vals)
        new_addr_str = geo_addr._rebuild_address_string()
        if new_addr_str != geo_addr.address_string:
            geo_addr.address_string = new_addr_str

    def _get_coords_from_geodata(self, partner):
        geo_addr = partner.geodata_address_id
        if not geo_addr:
            return False, False
        if geo_addr.latitude and geo_addr.longitude:
            return geo_addr.latitude, geo_addr.longitude
        if geo_addr.latitude_settlement and geo_addr.longitude_settlement:
            return geo_addr.latitude_settlement, geo_addr.longitude_settlement
        return False, False

    def _apply_geodata_coords(self, vals):
        if len(self) == 1 and self.geodata_address_id:
            lat, lng = self._get_coords_from_geodata(self)
            if lat and lng:
                vals["partner_latitude"] = lat
                vals["partner_longitude"] = lng
            return False
        if len(self) > 1:
            for partner in self:
                vals_copy = dict(vals)
                if partner.geodata_address_id:
                    lat, lng = self._get_coords_from_geodata(partner)
                    if lat and lng:
                        vals_copy["partner_latitude"] = lat
                        vals_copy["partner_longitude"] = lng
                super(ResPartner, partner).write(vals_copy)
            return True
        return False

    def write(self, vals):
        address_fields = {
            "street",
            "zip",
            "city",
            "state_id",
            "country_id",
            "area",
            "hromada",
        }

        if self.env.context.get("geodata_applying"):
            return super().write(vals)

        has_address_change = any(f in vals for f in address_fields)

        if has_address_change and "geodata_address_id" not in vals:
            for partner in self:
                self._update_geodata_on_address_change(partner, vals)

            no_coords = (
                "partner_latitude" not in vals and "partner_longitude" not in vals
            )
            if no_coords and self._apply_geodata_coords(vals):
                return True

        return super().write(vals)

    def action_open_geodata_wizard(self):
        self.ensure_one()
        return {
            "name": _("Select Address from Geodata"),
            "type": "ir.actions.act_window",
            "res_model": "geodata.address.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_partner_id": self.id,
                "active_model": self._name,
                "active_id": self.id,
            },
        }

    _PARTNER_FIELD_API_KEYS = {
        "city": ("City", "SettlementType"),
        "street": ("Street", "StrType", "StreetType", "HouseNum"),
        "street2": ("ApartmentType", "Apartment", "AdditionAddress"),
        "zip": ("Index_", "Index_8x"),
        "state_id": ("Region",),
        "area": ("Area",),
        "hromada": ("Hromada",),
        "partner_latitude": ("Lat_", "Lat", "Lat_S"),
        "partner_longitude": ("Long_", "Long", "Long_S"),
    }

    _PARTNER_HIERARCHY_CLEAR = {
        "City": ["street", "street2", "zip", "partner_latitude", "partner_longitude"],
        "Street": ["street2", "zip"],
    }

    @classmethod
    def _get_partner_hierarchy_clear(cls, api_data):
        clear = set()
        for api_key, clear_list in cls._PARTNER_HIERARCHY_CLEAR.items():
            if api_key in api_data:
                for f in clear_list:
                    own_keys = cls._PARTNER_FIELD_API_KEYS.get(f, ())
                    if not any(k in api_data for k in own_keys):
                        clear.add(f)
        return clear

    @classmethod
    def _filter_by_api_keys(cls, vals, api_data):
        clear_fields = cls._get_partner_hierarchy_clear(api_data)
        filtered = {}
        for key, val in vals.items():
            api_keys = cls._PARTNER_FIELD_API_KEYS.get(key)
            if api_keys is None:
                filtered[key] = val
            elif any(k in api_data for k in api_keys):
                filtered[key] = val
            elif key in clear_fields:
                filtered[key] = val
        return filtered

    @api.model
    def _build_partner_vals(self, geo_address, api_data):
        partner_vals = geo_address.to_address_dict(for_js=True)
        partner_vals["partner_latitude"] = partner_vals.pop("latitude", 0)
        partner_vals["partner_longitude"] = partner_vals.pop("longitude", 0)
        partner_vals["geodata_address_id"] = [
            geo_address.id,
            geo_address.name or geo_address.address_string or "",
        ]
        partner_vals["geodata_autocomplete_active"] = True
        return partner_vals

    @api.model
    def _write_partner_from_vals(self, partner, geo_address, partner_vals, api_data):
        write_vals = self._filter_by_api_keys(partner_vals, api_data)
        write_partner = {}
        for f in ("street", "street2", "city", "zip", "area", "hromada"):
            if f in write_vals:
                write_partner[f] = write_vals[f]
        if "state_id" in write_vals:
            state = write_vals.get("state_id")
            write_partner["state_id"] = state[0] if isinstance(state, list) else state
        country = partner_vals.get("country_id")
        write_partner["country_id"] = (
            country[0] if isinstance(country, list) else country
        )
        if "partner_latitude" in write_vals:
            write_partner["partner_latitude"] = write_vals.get("partner_latitude", 0)
        if "partner_longitude" in write_vals:
            write_partner["partner_longitude"] = write_vals.get("partner_longitude", 0)
        write_partner["geodata_address_id"] = geo_address.id
        partner.with_context(geodata_applying=True).write(write_partner)

    @api.model
    def apply_address_to_partner(self, partner_id, api_data):
        if not api_data:
            return {}

        partner, geo_address = self._resolve_geodata_address(partner_id, api_data)
        if not geo_address:
            return {}

        partner_vals = self._build_partner_vals(geo_address, api_data)

        if partner and partner.exists():
            self._write_partner_from_vals(partner, geo_address, partner_vals, api_data)

        return self._filter_by_api_keys(partner_vals, api_data)
