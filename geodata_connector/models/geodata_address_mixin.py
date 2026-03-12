import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class GeodataAddressMixin(models.AbstractModel):
    _name = "geodata.address.mixin"
    _description = "Geodata Address Mixin"

    _GEODATA_FIELD_MAP = {
        "street": "street",
        "street2": "street2",
        "city": "city",
        "zip": "zip",
        "state_id": "state_id",
        "country_id": "country_id",
        "area": "area",
        "hromada": "hromada",
        "latitude": False,
        "longitude": False,
    }

    _GEODATA_API_KEYS = {
        "city": ("City", "SettlementType"),
        "street": ("Street", "StrType", "StreetType", "HouseNum", "HouseNumAdd"),
        "street2": ("ApartmentType", "Apartment", "AdditionAddress"),
        "zip": ("Index_", "Index_8x"),
        "state_id": ("Region",),
        "area": ("Area",),
        "hromada": ("Hromada",),
        "latitude": ("Lat_", "Lat", "Lat_S"),
        "longitude": ("Long_", "Long", "Long_S"),
    }

    _GEODATA_HIERARCHY_CLEAR = {
        "City": ["street", "street2", "zip", "latitude", "longitude"],
        "Street": ["street2", "zip"],
    }

    geodata_address_id = fields.Many2one(
        comodel_name="geodata.address",
        string="Geodata Address",
        ondelete="set null",
        copy=False,
    )
    geodata_autocomplete_active = fields.Boolean(
        store=False,
        default=False,
    )
    geodata_city_moniker = fields.Char(
        related="geodata_address_id.city_moniker",
        readonly=False,
        store=True,
        copy=False,
    )
    geodata_street_moniker = fields.Char(
        related="geodata_address_id.street_moniker",
        readonly=False,
        store=True,
        copy=False,
    )
    has_geodata_credential = fields.Boolean(
        compute="_compute_has_geodata_credential",
        compute_sudo=True,
        store=False,
    )
    geodata_store_english = fields.Boolean(
        compute="_compute_geodata_settings",
        compute_sudo=True,
    )
    geodata_store_russian = fields.Boolean(
        compute="_compute_geodata_settings",
        compute_sudo=True,
    )

    def _compute_has_geodata_credential(self):
        credential = self.env["geodata.api.credential"].sudo().get_credential()
        has_credential = bool(credential)
        for record in self:
            record.has_geodata_credential = has_credential

    def _compute_geodata_settings(self):
        credential = self.env["geodata.api.credential"].sudo().get_credential()
        store_en = credential.store_english if credential else True
        store_ru = credential.store_russian if credential else False
        for record in self:
            record.geodata_store_english = store_en
            record.geodata_store_russian = store_ru

    def _ensure_geodata_address(self):
        self.ensure_one()
        if not self.geodata_address_id:
            address = self.env["geodata.address"].create({})
            super().write({"geodata_address_id": address.id})
            self.invalidate_recordset(["geodata_address_id"])
        return self.geodata_address_id

    @api.model
    def _resolve_geodata_address(self, record_id, api_data):
        existing_addr_id = api_data.pop("_geodata_address_id", False)
        record = False
        if record_id:
            record = self.browse(record_id)
            if not record.exists():
                return False, False
            geo_address = record._ensure_geodata_address()
        elif existing_addr_id:
            geo_address = self.env["geodata.address"].browse(existing_addr_id)
            if not geo_address.exists():
                geo_address = False
        else:
            geo_address = False
        if geo_address:
            geo_address.update_from_api_response(api_data)
        else:
            geo_address = self.env["geodata.address"].create_from_api_response(api_data)
        return record, geo_address

    @api.model
    def _build_geodata_vals(self, geo_address, api_data):
        addr_dict = geo_address.to_address_dict(for_js=True)
        field_map = self._GEODATA_FIELD_MAP

        vals = {}
        for std_field, real_field in field_map.items():
            if not real_field:
                continue
            if std_field in addr_dict:
                vals[real_field] = addr_dict[std_field]

        lat_field = field_map.get("latitude")
        if lat_field:
            vals[lat_field] = addr_dict.get("latitude", 0)
        lng_field = field_map.get("longitude")
        if lng_field:
            vals[lng_field] = addr_dict.get("longitude", 0)

        vals["geodata_address_id"] = [
            geo_address.id,
            geo_address.name or geo_address.address_string or "",
        ]
        vals["geodata_autocomplete_active"] = True
        return vals

    @api.model
    def _get_hierarchy_clear_std_fields(self, api_data):
        clear = set()
        for api_key, std_fields in self._GEODATA_HIERARCHY_CLEAR.items():
            if api_key in api_data:
                for sf in std_fields:
                    own_keys = self._GEODATA_API_KEYS.get(sf, ())
                    if not any(k in api_data for k in own_keys):
                        clear.add(sf)
        return clear

    @api.model
    def _filter_geodata_by_api_keys(self, vals, api_data):
        field_map = self._GEODATA_FIELD_MAP
        api_keys = self._GEODATA_API_KEYS
        reverse_map = {}
        for std_field, real_field in field_map.items():
            if real_field:
                reverse_map[real_field] = std_field

        clear_fields = self._get_hierarchy_clear_std_fields(api_data)

        filtered = {}
        for key, val in vals.items():
            std_field = reverse_map.get(key, key)
            keys = api_keys.get(std_field)
            if keys is None:
                filtered[key] = val
            elif any(k in api_data for k in keys):
                filtered[key] = val
            elif std_field in clear_fields:
                filtered[key] = val
        return filtered

    @api.model
    def _write_geodata_vals(self, record, geo_address, vals, api_data):
        write_vals = self._filter_geodata_by_api_keys(vals, api_data)
        fmap = self._GEODATA_FIELD_MAP
        result = {}

        for std in ("street", "street2", "city", "zip", "area", "hromada"):
            rf = fmap.get(std)
            if rf and rf in write_vals:
                result[rf] = write_vals[rf]

        for std in ("state_id", "country_id"):
            rf = fmap.get(std)
            if rf and rf in write_vals:
                val = write_vals[rf]
                result[rf] = val[0] if isinstance(val, list) else val
            elif std == "country_id" and rf:
                val = vals.get(rf)
                if val:
                    result[rf] = val[0] if isinstance(val, list) else val

        for std in ("latitude", "longitude"):
            rf = fmap.get(std)
            if rf and rf in write_vals:
                result[rf] = write_vals.get(rf, 0)

        result["geodata_address_id"] = geo_address.id
        record.with_context(geodata_applying=True).write(result)

    @api.model
    def apply_geodata_address(self, record_id, api_data):
        if not api_data:
            return {}

        record, geo_address = self._resolve_geodata_address(record_id, api_data)
        if not geo_address:
            return {}

        vals = self._build_geodata_vals(geo_address, api_data)

        if record and record.exists():
            self._write_geodata_vals(record, geo_address, vals, api_data)

        return self._filter_geodata_by_api_keys(vals, api_data)
