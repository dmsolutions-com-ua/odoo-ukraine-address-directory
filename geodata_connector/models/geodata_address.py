# pylint: disable=too-many-lines
import logging
import re

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

UKRAINE_STATES = {
    "Вінницька": "UA05",
    "Волинська": "UA07",
    "Дніпропетровська": "UA12",
    "Донецька": "UA14",
    "Житомирська": "UA18",
    "Закарпатська": "UA21",
    "Запорізька": "UA23",
    "Івано-Франківська": "UA26",
    "Київська": "UA32",
    "Кіровоградська": "UA35",
    "Луганська": "UA09",
    "Львівська": "UA46",
    "Миколаївська": "UA48",
    "Одеська": "UA51",
    "Полтавська": "UA53",
    "Рівненська": "UA56",
    "Сумська": "UA59",
    "Тернопільська": "UA61",
    "Харківська": "UA63",
    "Херсонська": "UA65",
    "Хмельницька": "UA68",
    "Черкаська": "UA71",
    "Чернівецька": "UA77",
    "Чернігівська": "UA74",
    "Київ": "UA30",
    "Севастополь": "UA40",
    "Автономна Республіка Крим": "UA43",
}


class GeodataAddress(models.Model):
    _name = "geodata.address"
    _description = "Geodata Address"
    _order = "create_date desc"

    _FIELD_API_KEYS = {
        "geodata_id": ("ID",),
        "settlement_ref": ("SettlementId",),
        "street_ref": ("StreetId",),
        "house_ref": ("HouseId",),
        "source_query": ("SourceAddress", "AddressString"),
        "address_string": ("AddressString",),
        "post_index": ("Index_", "Index_8x"),
        "region": ("Region",),
        "area": ("Area",),
        "city": ("City",),
        "settlement_type": ("SettlementType",),
        "street": ("Street",),
        "str_type": ("StrType", "StreetType"),
        "house_num": ("HouseNum",),
        "house_num_add": ("HouseNumAdd",),
        "apartment_type": ("ApartmentType",),
        "apartment": ("Apartment",),
        "addition_address": ("AdditionAddress",),
        "latitude": ("Lat_", "Lat"),
        "longitude": ("Long_", "Long"),
        "latitude_settlement": ("Lat_S", "Lat_", "Lat"),
        "longitude_settlement": ("Long_S", "Long_", "Long"),
        "koatuu": ("KOATUU",),
        "kato": ("KATO",),
        "hromada": ("Hromada",),
        "hromada_old": ("HromadaOld",),
        "phone_code": ("PhoneCode",),
        "is_regional_center": ("IsOCentre",),
        "is_district_center": ("IsRCentre",),
        "city_district": ("CityDistrict",),
        "metro_station": ("MetroStation",),
        "metro_line": ("MetroLine",),
        "metro_distance": ("MetroDistance",),
        "terr_status": ("TerrStatus",),
        "region_old": ("RegionOld",),
        "area_old": ("AreaOld",),
        "city_old": ("CityOld",),
        "settlement_type_old": ("SettlementTypeOld",),
        "str_type_old": ("StrTypeOld", "StreetTypeOld"),
        "street_old": ("StreetOld",),
        "comments": ("Comments",),
        "description": ("Description",),
        "city_moniker": ("st_moniker", "Moniker"),
        "street_moniker": (
            "str_moniker",
            "StrMoniker",
            "StreetMoniker",
            "house_moniker",
        ),
    }

    name = fields.Char(
        compute="_compute_name",
        store=True,
        help="Display name of the address",
    )
    geodata_id = fields.Integer(
        string="Geodata ID",
        help="Unique code from Geodata API",
    )
    settlement_ref = fields.Integer(
        string="Settlement ID",
        index=True,
        help="Unique settlement ID from Geodata API",
    )
    street_ref = fields.Integer(
        string="Street ID",
        index=True,
        help="Unique street ID from Geodata API",
    )
    house_ref = fields.Integer(
        string="House ID",
        index=True,
        help="Unique house ID from Geodata API",
    )
    source_query = fields.Char(
        help="Original search query from user",
    )
    address_string = fields.Char(
        string="Full Address",
        help="Complete address as single string",
    )
    post_index = fields.Char(
        string="Postal Code",
        help="Postal index/ZIP code",
    )
    region = fields.Char(
        help="Region/Oblast name",
        translate=True,
    )
    area = fields.Char(
        string="District",
        help="District/Raion name",
        translate=True,
    )
    city = fields.Char(
        string="City/Settlement",
        help="Settlement name",
        translate=True,
    )
    settlement_type = fields.Char(
        help="Type: city, village, township, etc.",
        translate=True,
    )
    street = fields.Char(
        string="Street Name",
        help="Street name without type prefix",
        translate=True,
    )
    str_type = fields.Char(
        string="Street Type",
        help="Street type: str., lane, etc.",
        translate=True,
    )
    house_num = fields.Char(
        string="House Number",
        help="Building number",
    )
    house_num_add = fields.Char(
        string="House Number Addition",
        help="Building letter, corpus, fraction",
    )
    house_num_add_en = fields.Char()
    house_num_add_ru = fields.Char()
    apartment_type = fields.Char(
        help="Type: apt., office, room",
        translate=True,
    )
    apartment = fields.Char(
        string="Apartment Number",
        help="Apartment/office number",
    )
    addition_address = fields.Char(
        string="Additional Address Info",
        help="Additional information: floor, etc.",
    )
    latitude = fields.Float(
        string="Building Latitude",
        digits=(10, 7),
        help="Geographic latitude of the building",
    )
    longitude = fields.Float(
        string="Building Longitude",
        digits=(10, 7),
        help="Geographic longitude of the building",
    )
    latitude_settlement = fields.Float(
        string="Settlement Latitude",
        digits=(10, 7),
        help="Geographic latitude of settlement center",
    )
    longitude_settlement = fields.Float(
        string="Settlement Longitude",
        digits=(10, 7),
        help="Geographic longitude of settlement center",
    )
    koatuu = fields.Char(
        string="KOATUU",
        help="KOATUU code (for compatibility)",
    )
    kato = fields.Char(
        help="KATOTTG code",
    )
    hromada = fields.Char(
        help="Territorial community name",
        translate=True,
    )
    hromada_old = fields.Char(
        string="Old Hromada Name",
        help="Previous territorial community name (if renamed)",
    )
    phone_code = fields.Char(
        help="Settlement phone code",
    )
    is_regional_center = fields.Boolean(
        string="Regional Center",
        help="Is regional center",
    )
    is_district_center = fields.Boolean(
        string="District Center",
        help="Is district center",
    )
    city_district = fields.Char(
        help="District of the city (if KATOTTG code exists)",
        translate=True,
    )
    metro_station = fields.Char(
        help="Nearest metro station",
    )
    metro_line = fields.Char(
        help="Nearest metro line",
    )
    metro_distance = fields.Char(
        help="Distance to metro (straight line)",
    )
    terr_status = fields.Char(
        string="Territory Status",
        help="Occupied territory status (as of 24.02.2022)",
    )
    region_old = fields.Char(
        string="Old Region Name",
        help="Previous region name (if renamed)",
    )
    area_old = fields.Char(
        string="Old District Name",
        help="Previous district name (if renamed/border changed)",
    )
    city_old = fields.Char(
        string="Old City Name",
        help="Previous city name (if renamed)",
    )
    settlement_type_old = fields.Char(
        string="Old Settlement Type",
        help="Previous settlement type (if changed)",
    )
    str_type_old = fields.Char(
        string="Old Street Type",
        help="Previous street type (if changed)",
    )
    street_old = fields.Char(
        string="Old Street Name",
        help="Previous street name (if renamed)",
    )
    city_moniker = fields.Char()
    street_moniker = fields.Char()
    comments = fields.Text()
    description = fields.Text()

    address_ua_postal = fields.Char(
        string="Address (UA Postal)",
        compute="_compute_address_formats",
        store=True,
        help="Ukrainian postal format: Index, Region, City, Street, House",
    )
    address_ua_short = fields.Char(
        string="Address (UA Short)",
        compute="_compute_address_formats",
        store=True,
        help="Ukrainian short format: City, Street, House",
    )
    address_western = fields.Char(
        string="Address (Western)",
        compute="_compute_address_formats",
        store=True,
        help="Western format: Street House, City, Zip",
    )

    address_full_ua = fields.Char(
        string="Full Address (UA)",
        compute="_compute_full_addresses",
        store=True,
        help="Full postal address in Ukrainian for contracts",
    )
    address_full_ru = fields.Char(
        string="Full Address (RU)",
        compute="_compute_full_addresses",
        store=True,
        help="Full postal address in Russian for contracts",
    )
    address_full_en = fields.Char(
        string="Full Address (EN)",
        compute="_compute_full_addresses",
        store=True,
        help="Full postal address in English for contracts",
    )

    address_letter_ua = fields.Char(
        string="Letter Address (UA)",
        compute="_compute_full_addresses",
        store=True,
        help="Address for letters in Ukrainian",
    )
    address_letter_ru = fields.Char(
        string="Letter Address (RU)",
        compute="_compute_full_addresses",
        store=True,
        help="Address for letters in Russian",
    )
    address_letter_en = fields.Char(
        string="Letter Address (EN)",
        compute="_compute_full_addresses",
        store=True,
        help="Address for letters in English",
    )

    city_en = fields.Char(string="City (English)")
    city_ru = fields.Char(string="City (Russian)")
    street_en = fields.Char(string="Street (English)")
    street_ru = fields.Char(string="Street (Russian)")
    area_en = fields.Char(string="Area (English)")
    area_ru = fields.Char(string="Area (Russian)")
    hromada_en = fields.Char(string="Hromada (English)")
    hromada_ru = fields.Char(string="Hromada (Russian)")
    region_en = fields.Char(string="Region (English)")
    region_ru = fields.Char(string="Region (Russian)")
    city_district_en = fields.Char(string="City District (English)")
    city_district_ru = fields.Char(string="City District (Russian)")
    settlement_type_en = fields.Char(string="Settlement Type (English)")
    settlement_type_ru = fields.Char(string="Settlement Type (Russian)")
    str_type_en = fields.Char(string="Street Type (English)")
    str_type_ru = fields.Char(string="Street Type (Russian)")
    apartment_type_en = fields.Char(string="Apartment Type (English)")
    apartment_type_ru = fields.Char(string="Apartment Type (Russian)")
    city_old_en = fields.Char(string="Old City (English)")
    city_old_ru = fields.Char(string="Old City (Russian)")
    area_old_en = fields.Char(string="Old Area (English)")
    area_old_ru = fields.Char(string="Old Area (Russian)")
    street_old_en = fields.Char(string="Old Street (English)")
    street_old_ru = fields.Char(string="Old Street (Russian)")
    str_type_old_en = fields.Char(string="Old Street Type (English)")
    str_type_old_ru = fields.Char(string="Old Street Type (Russian)")

    @api.model
    def fields_view_get(
        self, view_id=None, view_type="form", toolbar=False, submenu=False
    ):
        res = super().fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu
        )

        credential = self.env["geodata.api.credential"].sudo().get_credential()
        if "context" not in res:
            res["context"] = {}

        res["context"]["geodata_store_english"] = (
            credential.store_english if credential else True
        )
        res["context"]["geodata_store_russian"] = (
            credential.store_russian if credential else False
        )

        return res

    @api.depends(
        "region",
        "area",
        "settlement_type",
        "city",
        "str_type",
        "street",
        "house_num",
        "house_num_add",
        "street_old",
        "str_type_old",
        "city_old",
        "area_old",
    )
    def _compute_name(self):
        for record in self:
            record.name = record._rebuild_address_string() or _("New Address")

    @api.depends(
        "city",
        "street",
        "house_num",
        "post_index",
        "region",
        "area",
        "hromada",
        "settlement_type",
        "str_type",
        "house_num_add",
        "apartment",
        "apartment_type",
    )
    def _compute_address_formats(self):
        for record in self:
            record.address_ua_postal = record.format_address_ua_postal()
            record.address_ua_short = record.format_address_ua_short()
            record.address_western = record.format_address_western()

    @api.depends(
        "post_index",
        "region",
        "area",
        "settlement_type",
        "city",
        "str_type",
        "street",
        "house_num",
        "house_num_add",
        "street_old",
        "str_type_old",
        "city_old",
        "area_old",
        "region_en",
        "area_en",
        "settlement_type_en",
        "city_en",
        "str_type_en",
        "street_en",
        "city_old_en",
        "area_old_en",
        "street_old_en",
        "str_type_old_en",
        "region_ru",
        "area_ru",
        "settlement_type_ru",
        "city_ru",
        "str_type_ru",
        "street_ru",
        "city_old_ru",
        "area_old_ru",
        "street_old_ru",
        "str_type_old_ru",
    )
    def _compute_full_addresses(self):
        credential = self.env["geodata.api.credential"].sudo().get_credential()
        store_en = credential.store_english if credential else True
        store_ru = credential.store_russian if credential else False
        for record in self:
            record.address_full_ua = record._format_full_address("ua")
            record.address_letter_ua = record._format_letter_address("ua")
            if store_en:
                record.address_full_en = record._format_full_address("en")
                record.address_letter_en = record._format_letter_address("en")
            else:
                record.address_full_en = ""
                record.address_letter_en = ""
            if store_ru:
                record.address_full_ru = record._format_full_address("ru")
                record.address_letter_ru = record._format_letter_address("ru")
            else:
                record.address_full_ru = ""
                record.address_letter_ru = ""

    def _get_template_values(self, lang="ua"):
        if lang == "ua":
            country = "УКРАЇНА"
        elif lang == "ru":
            country = "УКРАИНА"
        else:
            country = "Ukraine"

        region = self._get_field_by_lang("region", lang)
        area = self._get_field_by_lang("area", lang)
        hromada = self._get_field_by_lang("hromada", lang)

        house_part = self.house_num or ""
        house_add = self._get_field_by_lang("house_num_add", lang)
        if house_add:
            house_part = f"{house_part}{house_add}"

        apt_parts = [p for p in [self.apartment_type, self.apartment] if p]

        str_type = self._get_field_by_lang("str_type", lang)
        street = self._get_field_by_lang("street", lang)
        street_val = f"{str_type} {street}" if str_type and street else street

        settlement_type = self._get_field_by_lang("settlement_type", lang)
        city = self._get_field_by_lang("city", lang)
        city_val = f"{settlement_type} {city}" if settlement_type and city else city

        region_old = self._get_old_name_by_lang("region_old", lang)
        area_old_val = self._get_old_name_by_lang("area_old", lang)
        city_old_val = self._get_old_name_by_lang("city_old", lang)
        street_old_val = self._get_old_name_by_lang("street_old", lang)

        return {
            "country": country,
            "index": self.post_index or "",
            "region": region or "",
            "area": area or "",
            "hromada": hromada or "",
            "city": city_val or "",
            "street": street_val or "",
            "house": house_part or "",
            "apartment": " ".join(apt_parts) if apt_parts else "",
            "region_old": f"({region_old})" if region_old else "",
            "area_old": f"({area_old_val})" if area_old_val else "",
            "city_old": f"({city_old_val})" if city_old_val else "",
            "street_old": f"({street_old_val})" if street_old_val else "",
        }

    def _render_address_template(self, template, lang="ua"):
        self.ensure_one()
        values = self._get_template_values(lang)

        tokens = re.split(r"(\{[^}]+\})", template)
        parts = []
        pending_sep = ""
        for token in tokens:
            match = re.match(r"^\{(\w+)\}$", token)
            if match:
                val = values.get(match.group(1), "")
                if val:
                    if parts:
                        parts.append(pending_sep)
                    parts.append(val)
                pending_sep = ""
            else:
                pending_sep = token

        return "".join(parts).strip().rstrip(",").strip()

    def _format_region_part(self, lang):
        return self._get_field_by_lang("region", lang) or ""

    def _format_area_part(self, lang):
        return self._format_area_with_old(lang) or ""

    def _format_street_house_part(self, lang):
        street_with_old = self._format_street_with_old(lang)
        house_part = self.house_num or ""
        house_add = self._get_field_by_lang("house_num_add", lang)
        if house_add:
            house_part = f"{house_part}{house_add}"
        if street_with_old and house_part:
            return f"{street_with_old}, {house_part}"
        return street_with_old or house_part

    def _collect_address_parts(self, lang):
        parts = []
        if self.post_index:
            parts.append(self.post_index)
        region = self._format_region_part(lang)
        if region:
            parts.append(region)
        area = self._format_area_part(lang)
        if area:
            parts.append(area)
        city_part = self._format_city_with_old(lang)
        if city_part:
            parts.append(city_part)
        street_house = self._format_street_house_part(lang)
        if street_house:
            parts.append(street_house)
        return parts

    def _format_full_address(self, lang="ua"):
        """Format full postal address for contracts."""
        credential = self.env["geodata.api.credential"].sudo().get_credential()
        if credential and credential.address_format_document:
            return self._render_address_template(
                credential.address_format_document, lang
            )
        country_map = {"ua": "УКРАЇНА", "ru": "УКРАИНА"}
        parts = [country_map.get(lang, "Ukraine")]
        parts.extend(self._collect_address_parts(lang))
        return ", ".join(parts)

    def _format_letter_address(self, lang="ua"):
        """Format address for letters (without country)."""
        credential = self.env["geodata.api.credential"].sudo().get_credential()
        if credential and credential.address_format_letter:
            return self._render_address_template(credential.address_format_letter, lang)
        return ", ".join(self._collect_address_parts(lang))

    def _get_field_by_lang(self, field_name, lang):
        """Get field value by language suffix."""
        if lang == "ua":
            return getattr(self, field_name, "") or ""
        translated_field = f"{field_name}_{lang}"
        value = getattr(self, translated_field, "") or ""
        if not value:
            value = getattr(self, field_name, "") or ""
        return value

    def _get_old_name_by_lang(self, field_name, lang):
        if lang == "ua":
            return getattr(self, field_name, "") or ""
        translated_field = f"{field_name}_{lang}"
        value = getattr(self, translated_field, "") or ""
        if not value:
            value = getattr(self, field_name, "") or ""
        return value

    def _format_street_with_old(self, lang="ua"):
        str_type = self._get_field_by_lang("str_type", lang)
        street = self._get_field_by_lang("street", lang)
        if not street:
            return ""
        street_part = f"{str_type} {street}" if str_type else street
        street_old = self._get_old_name_by_lang("street_old", lang)
        if street_old and street_old.lower() != street.lower():
            str_type_old = self._get_old_name_by_lang("str_type_old", lang)
            old_part = f"{str_type_old} {street_old}" if str_type_old else street_old
            street_part = f"{street_part} ({old_part})"
        return street_part

    def _format_city_with_old(self, lang="ua"):
        settlement_type = self._get_field_by_lang("settlement_type", lang)
        city = self._get_field_by_lang("city", lang)
        if not city:
            return ""
        city_part = f"{settlement_type} {city}" if settlement_type else city
        city_old = self._get_old_name_by_lang("city_old", lang)
        if city_old and city_old.lower() != city.lower():
            city_part = f"{city_part} ({city_old})"
        return city_part

    def _format_area_with_old(self, lang="ua"):
        area = self._get_field_by_lang("area", lang)
        if not area:
            return ""
        area_old = self._get_old_name_by_lang("area_old", lang)
        if area_old and area_old.lower() != area.lower():
            area = f"{area} ({area_old})"
        return area

    def _format_hromada_with_old(self, lang="ua"):
        hromada = self._get_field_by_lang("hromada", lang)
        if not hromada:
            return ""
        hromada_old = self.hromada_old or ""
        if hromada_old and hromada_old.lower() != hromada.lower():
            hromada = f"{hromada} ({hromada_old})"
        return hromada

    # pylint: disable=too-many-branches,too-many-return-statements
    def format_address_ua_postal(self):
        parts = []
        if self.post_index:
            parts.append(self.post_index)
        if self.region:
            parts.append(self.region)
        if self.area:
            parts.append(self.area)
        if self.hromada:
            parts.append(self.hromada)
        if self.settlement_type and self.city:
            parts.append(f"{self.settlement_type} {self.city}")
        elif self.city:
            parts.append(self.city)
        if self.str_type and self.street:
            parts.append(f"{self.str_type} {self.street}")
        elif self.street:
            parts.append(self.street)
        if self.house_num:
            house = self.house_num
            if self.house_num_add:
                house += self.house_num_add
            parts.append(house)
        if self.apartment_type and self.apartment:
            parts.append(f"{self.apartment_type} {self.apartment}")
        elif self.apartment:
            parts.append(f"кв. {self.apartment}")
        return ", ".join(parts)

    def format_address_ua_short(self):
        parts = []
        if self.city:
            parts.append(self.city)
        if self.str_type and self.street:
            parts.append(f"{self.str_type} {self.street}")
        elif self.street:
            parts.append(self.street)
        if self.house_num:
            house = self.house_num
            if self.house_num_add:
                house += self.house_num_add
            parts.append(house)
        if self.apartment:
            parts.append(f"кв. {self.apartment}")
        return ", ".join(parts)

    def format_address_western(self):
        parts = []
        street_part = []
        if self.street_en or self.street:
            street_part.append(self.street_en or self.street)
        if self.str_type_en:
            street_part.append(self.str_type_en)
        elif self.str_type:
            street_part.append(self._translate_str_type(self.str_type))
        if self.house_num:
            street_part.append(self.house_num)
        if street_part:
            parts.append(" ".join(street_part))
        if self.city_en or self.city:
            parts.append(self.city_en or self.city)
        if self.post_index:
            parts.append(self.post_index)
        return ", ".join(parts)

    def _translate_str_type(self, str_type):
        translations = {
            "вул.": "St.",
            "пр.": "Ave.",
            "пр-т": "Ave.",
            "просп.": "Ave.",
            "бул.": "Blvd.",
            "б-р": "Blvd.",
            "пров.": "Ln.",
            "пл.": "Sq.",
            "наб.": "Emb.",
            "шосе": "Hwy.",
            "алея": "Alley",
            "узвіз": "Descent",
        }
        return translations.get(str_type, str_type)

    @api.model
    def _build_address_string(self, api_data):
        parts = []

        if api_data.get("Region"):
            parts.append(api_data["Region"])
        if api_data.get("Area"):
            parts.append(api_data["Area"])
        if api_data.get("SettlementType"):
            parts.append(api_data["SettlementType"])
        if api_data.get("City"):
            parts.append(api_data["City"])

        street_parts = []
        if api_data.get("StrType"):
            street_parts.append(api_data["StrType"])
        if api_data.get("Street"):
            street_parts.append(api_data["Street"])
        if street_parts:
            parts.append(" ".join(street_parts))

        if api_data.get("HouseNum"):
            house = api_data["HouseNum"]
            if api_data.get("HouseNumAdd"):
                house += api_data["HouseNumAdd"]
            parts.append(house)

        if api_data.get("ApartmentType") and api_data.get("Apartment"):
            parts.append(f"{api_data['ApartmentType']} {api_data['Apartment']}")
        elif api_data.get("Apartment"):
            parts.append(f"кв. {api_data['Apartment']}")

        result = ", ".join(parts) if parts else ""
        return result or api_data.get("SourceAddress", "")

    def update_from_geodata_address(self, source_address):
        self.ensure_one()
        if not source_address:
            return False

        vals = {
            "geodata_id": source_address.geodata_id,
            "settlement_ref": source_address.settlement_ref,
            "street_ref": source_address.street_ref,
            "house_ref": source_address.house_ref,
            "source_query": source_address.source_query,
            "address_string": source_address.address_string,
            "post_index": source_address.post_index,
            "region": source_address.region,
            "area": source_address.area,
            "city": source_address.city,
            "settlement_type": source_address.settlement_type,
            "street": source_address.street,
            "str_type": source_address.str_type,
            "house_num": source_address.house_num,
            "house_num_add": source_address.house_num_add,
            "apartment_type": source_address.apartment_type,
            "apartment": source_address.apartment,
            "addition_address": source_address.addition_address,
            "latitude": source_address.latitude,
            "longitude": source_address.longitude,
            "latitude_settlement": source_address.latitude_settlement,
            "longitude_settlement": source_address.longitude_settlement,
            "koatuu": source_address.koatuu,
            "kato": source_address.kato,
            "hromada": source_address.hromada,
            "hromada_old": source_address.hromada_old,
            "phone_code": source_address.phone_code,
            "is_regional_center": source_address.is_regional_center,
            "is_district_center": source_address.is_district_center,
            "city_district": source_address.city_district,
            "metro_station": source_address.metro_station,
            "metro_line": source_address.metro_line,
            "metro_distance": source_address.metro_distance,
            "terr_status": source_address.terr_status,
            "region_old": source_address.region_old,
            "area_old": source_address.area_old,
            "city_old": source_address.city_old,
            "settlement_type_old": source_address.settlement_type_old,
            "str_type_old": source_address.str_type_old,
            "street_old": source_address.street_old,
            "comments": source_address.comments,
            "description": source_address.description,
            "city_moniker": source_address.city_moniker,
            "street_moniker": source_address.street_moniker,
        }

        vals = {k: v for k, v in vals.items() if v is not None}

        self.write(vals)
        return True

    @api.model
    def _api_data_to_vals(self, api_data):
        address_string = api_data.get("AddressString") or self._build_address_string(
            api_data
        )
        return {
            "geodata_id": api_data.get("ID"),
            "settlement_ref": api_data.get("SettlementId"),
            "street_ref": api_data.get("StreetId"),
            "house_ref": api_data.get("HouseId"),
            "source_query": api_data.get("SourceAddress") or address_string,
            "address_string": address_string,
            "post_index": api_data.get("Index_") or api_data.get("Index_8x"),
            "region": api_data.get("Region"),
            "area": api_data.get("Area"),
            "city": api_data.get("City"),
            "settlement_type": api_data.get("SettlementType"),
            "street": api_data.get("Street"),
            "str_type": (api_data.get("StrType") or api_data.get("StreetType")),
            "house_num": api_data.get("HouseNum"),
            "house_num_add": api_data.get("HouseNumAdd"),
            "apartment_type": api_data.get("ApartmentType"),
            "apartment": api_data.get("Apartment"),
            "addition_address": api_data.get("AdditionAddress"),
            "latitude": (
                float(api_data["Lat_"])
                if (api_data.get("Lat_") and api_data.get("Street"))
                else (
                    float(api_data["Lat"])
                    if (api_data.get("Lat") and api_data.get("Street"))
                    else None
                )
            ),
            "longitude": (
                float(api_data["Long_"])
                if (api_data.get("Long_") and api_data.get("Street"))
                else (
                    float(api_data["Long"])
                    if (api_data.get("Long") and api_data.get("Street"))
                    else None
                )
            ),
            "latitude_settlement": (
                float(api_data["Lat_S"])
                if api_data.get("Lat_S")
                else (
                    float(api_data["Lat_"])
                    if (api_data.get("Lat_") and not api_data.get("Street"))
                    else (
                        float(api_data["Lat"])
                        if (api_data.get("Lat") and not api_data.get("Street"))
                        else None
                    )
                )
            ),
            "longitude_settlement": (
                float(api_data["Long_S"])
                if api_data.get("Long_S")
                else (
                    float(api_data["Long_"])
                    if (api_data.get("Long_") and not api_data.get("Street"))
                    else (
                        float(api_data["Long"])
                        if (api_data.get("Long") and not api_data.get("Street"))
                        else None
                    )
                )
            ),
            "koatuu": api_data.get("KOATUU"),
            "kato": api_data.get("KATO"),
            "hromada": api_data.get("Hromada"),
            "hromada_old": api_data.get("HromadaOld"),
            "phone_code": api_data.get("PhoneCode"),
            "is_regional_center": api_data.get("IsOCentre", False),
            "is_district_center": api_data.get("IsRCentre", False),
            "city_district": api_data.get("CityDistrict"),
            "metro_station": api_data.get("MetroStation"),
            "metro_line": api_data.get("MetroLine"),
            "metro_distance": api_data.get("MetroDistance"),
            "terr_status": api_data.get("TerrStatus"),
            "region_old": api_data.get("RegionOld"),
            "area_old": api_data.get("AreaOld"),
            "city_old": api_data.get("CityOld"),
            "settlement_type_old": api_data.get("SettlementTypeOld"),
            "str_type_old": api_data.get("StrTypeOld"),
            "street_old": api_data.get("StreetOld"),
            "comments": api_data.get("Comments"),
            "description": api_data.get("Description"),
            "city_moniker": (
                api_data.get("st_moniker", "") or api_data.get("Moniker", "")
            )
            or None,
            "street_moniker": (
                api_data.get("str_moniker", "")
                or api_data.get("StrMoniker", "")
                or api_data.get("StreetMoniker", "")
                or api_data.get("house_moniker", "")
            )
            or None,
        }

    @api.model
    def create_from_api_response(self, api_data):
        if not isinstance(api_data, dict):
            return self.env["geodata.address"]

        vals = self._api_data_to_vals(api_data)
        vals = {k: v for k, v in vals.items() if v is not None}

        record = self.create(vals)
        record.fetch_translations()
        return record

    def _rebuild_address_string(self):
        self.ensure_one()
        parts = []
        if self.region:
            parts.append(self.region)
        if self.area:
            area_part = self._format_area_with_old("ua")
            if area_part:
                parts.append(area_part)
        if self.settlement_type and self.city:
            parts.append(f"{self.settlement_type} {self.city}")
        elif self.city:
            parts.append(self.city)
        elif self.settlement_type:
            parts.append(self.settlement_type)
        street_with_old = self._format_street_with_old("ua")
        if street_with_old:
            parts.append(street_with_old)
        if self.house_num:
            house = self.house_num
            if self.house_num_add:
                house += self.house_num_add
            parts.append(house)
        return ", ".join(parts)

    _PRESERVE_WHEN_EMPTY = frozenset(
        {
            "region",
            "area",
            "hromada",
            "city",
            "settlement_type",
            "city_district",
            "settlement_ref",
            "city_moniker",
            "koatuu",
            "kato",
            "phone_code",
            "is_regional_center",
            "is_district_center",
            "metro_station",
            "metro_line",
            "metro_distance",
            "terr_status",
            "region_old",
            "area_old",
            "city_old",
            "settlement_type_old",
            "hromada_old",
            "latitude_settlement",
            "longitude_settlement",
        }
    )

    _HIERARCHY_CLEAR_DOWN = {
        "City": [
            "region",
            "area",
            "hromada",
            "city_district",
            "street",
            "str_type",
            "house_num",
            "house_num_add",
            "apartment_type",
            "apartment",
            "addition_address",
            "post_index",
            "latitude",
            "longitude",
            "street_ref",
            "house_ref",
        ],
        "Street": [
            "house_num",
            "house_num_add",
            "apartment_type",
            "apartment",
            "addition_address",
            "post_index",
            "latitude",
            "longitude",
            "house_ref",
        ],
        "HouseNum": [
            "house_num_add",
            "apartment_type",
            "apartment",
            "addition_address",
        ],
    }

    def _get_hierarchy_clear_fields(self, api_data):
        clear_fields = set()
        for api_key, clear_list in self._HIERARCHY_CLEAR_DOWN.items():
            if api_key in api_data:
                for f in clear_list:
                    own_keys = self._FIELD_API_KEYS.get(f, ())
                    if not any(k in api_data for k in own_keys):
                        clear_fields.add(f)
        return clear_fields

    _OLD_NAME_PARENTS = {
        "region_old": "region",
        "area_old": "area",
        "city_old": "city",
        "settlement_type_old": "settlement_type",
        "str_type_old": "str_type",
        "street_old": "street",
        "hromada_old": "hromada",
    }

    def update_from_api_response(self, api_data):
        self.ensure_one()
        if not isinstance(api_data, dict):
            return

        vals = self._api_data_to_vals(api_data)
        filtered = {}
        coord_preserve = (
            "latitude_settlement",
            "longitude_settlement",
            "latitude",
            "longitude",
        )
        for field, value in vals.items():
            api_keys = self._FIELD_API_KEYS.get(field, ())
            has_key = any(k in api_data for k in api_keys)
            if not has_key:
                continue
            if value is None:
                value = False
            if value == "" and field in self._PRESERVE_WHEN_EMPTY:
                continue
            if value == "":
                value = False
            if not value and field in coord_preserve and getattr(self, field, 0):
                continue
            filtered[field] = value

        for field in self._get_hierarchy_clear_fields(api_data):
            if field not in filtered:
                filtered[field] = False

        for old_field, parent_field in self._OLD_NAME_PARENTS.items():
            if parent_field in filtered and old_field not in filtered:
                filtered[old_field] = False

        if filtered:
            self.write(filtered)
        self.fetch_translations()

    def _validate_translation_match(self, api_data):
        if self.house_ref and api_data.get("HouseId"):
            return str(self.house_ref) == str(api_data["HouseId"])
        if self.street_ref and api_data.get("StreetId"):
            return str(self.street_ref) == str(api_data["StreetId"])
        if self.settlement_ref and api_data.get("SettlementId"):
            return self.settlement_ref == api_data["SettlementId"]
        return True

    def _find_matching_result(self, results):
        if not results:
            return None
        items = results if isinstance(results, list) else [results]
        for item in items:
            if self._validate_translation_match(item):
                return item
        return None

    def _fetch_translation_data(self, credential, query, lang):
        lang_label = lang[:2].upper()
        try:
            results = credential.api_full_address(sRequest=query, sLang=lang)
            if not results:
                _logger.debug(
                    "%s translation: empty result for query %s", lang_label, query
                )
                return None
            match = self._find_matching_result(results)
            if match:
                _logger.debug("%s translation fetched successfully", lang_label)
                return match
            _logger.debug(
                "%s translation: no matching result for address %s "
                "(KOATUU=%s), skipping",
                lang_label,
                self.id,
                self.koatuu,
            )
            return None
        except Exception as e:
            _logger.debug("Failed to fetch %s translation: %s", lang_label, str(e))
            return None

    def _extract_translation_fields(self, api_data, suffix):
        return {
            f"city_{suffix}": api_data.get("City") or False,
            f"street_{suffix}": api_data.get("Street") or False,
            f"area_{suffix}": api_data.get("Area") or False,
            f"hromada_{suffix}": api_data.get("Hromada") or False,
            f"region_{suffix}": api_data.get("Region") or False,
            f"city_district_{suffix}": api_data.get("CityDistrict") or False,
            f"settlement_type_{suffix}": (api_data.get("SettlementType") or False),
            f"str_type_{suffix}": api_data.get("StrType") or False,
            f"city_old_{suffix}": api_data.get("CityOld") or False,
            f"area_old_{suffix}": api_data.get("AreaOld") or False,
            f"street_old_{suffix}": api_data.get("StreetOld") or False,
            f"str_type_old_{suffix}": api_data.get("StrTypeOld") or False,
            f"apartment_type_{suffix}": (api_data.get("ApartmentType") or False),
            f"house_num_add_{suffix}": api_data.get("HouseNumAdd") or False,
        }

    def _build_translation_query(self):
        parts = []
        if self.region:
            parts.append(self.region)
        if self.area:
            parts.append(self.area)
        if self.settlement_type and self.city:
            parts.append(f"{self.settlement_type} {self.city}")
        elif self.city:
            parts.append(self.city)
        if self.str_type and self.street:
            parts.append(f"{self.str_type} {self.street}")
        elif self.street:
            parts.append(self.street)
        if self.house_num:
            house = self.house_num
            if self.house_num_add:
                house += self.house_num_add
            parts.append(house)
        return ", ".join(parts) if parts else self.address_string

    _TRANSLATION_SUFFIXES = ("en", "ru")

    def _get_clear_translation_vals(self, suffix):
        return {
            f"{name}_{suffix}": False
            for name in (
                "city",
                "street",
                "area",
                "hromada",
                "region",
                "city_district",
                "settlement_type",
                "str_type",
                "city_old",
                "area_old",
                "street_old",
                "str_type_old",
                "apartment_type",
                "house_num_add",
            )
        }

    _UA_TRANSLATION_SKIP = frozenset(
        {
            "source_query",
            "settlement_ref",
            "street_ref",
            "house_ref",
            "city_moniker",
            "street_moniker",
            "koatuu",
            "kato",
        }
    )

    def _update_from_ua_translation(self, credential, query):
        api_data_ua = self._fetch_translation_data(credential, query, "uk_UA")
        if not api_data_ua:
            return
        ua_vals = self._api_data_to_vals(api_data_ua)
        filtered = {}
        for field, value in ua_vals.items():
            if field in self._UA_TRANSLATION_SKIP:
                continue
            if value is None:
                continue
            if value == "":
                value = False
            filtered[field] = value
        if filtered:
            _logger.debug(
                "UA translation updated %d fields for address %s",
                len(filtered),
                self.id,
            )
            self.write(filtered)

    def fetch_translations(self):
        self.ensure_one()
        query = self._build_translation_query()
        if not query:
            _logger.debug(
                "No address data for address %s, skipping translations", self.id
            )
            return

        credential = self.env["geodata.api.credential"].sudo().get_credential()
        if not credential:
            _logger.debug("No credential found, skipping translations")
            return

        _logger.debug(
            "Fetching translations for address %s, query: %s, "
            "store_en=%s, store_ru=%s",
            self.id,
            query,
            credential.store_english,
            credential.store_russian,
        )

        self._update_from_ua_translation(credential, query)

        vals = {}

        if credential.store_english:
            api_data_en = self._fetch_translation_data(
                credential,
                query,
                "en_US",
            )
            if api_data_en:
                vals.update(
                    self._extract_translation_fields(api_data_en, "en"),
                )
        else:
            vals.update(self._get_clear_translation_vals("en"))

        if credential.store_russian:
            api_data_ru = self._fetch_translation_data(
                credential,
                query,
                "ru_RU",
            )
            if api_data_ru:
                vals.update(
                    self._extract_translation_fields(api_data_ru, "ru"),
                )
        else:
            vals.update(self._get_clear_translation_vals("ru"))

        if vals:
            self.write(vals)

    def get_state_code_for_region(self, region):
        state_code = UKRAINE_STATES.get(region)
        if state_code:
            return state_code
        for state_name, code in UKRAINE_STATES.items():
            if state_name in region or region in state_name:
                return code
        region_short = region.replace("область", "").replace("обл.", "").strip()
        return f"UA-{region_short[:3].upper()}"

    def find_or_create_state(self, region, country_ua):
        State = self.env["res.country.state"]
        state = State.search(
            [
                ("name", "=", region),
                ("country_id", "=", country_ua.id),
            ],
            limit=1,
        )
        if state:
            return state.id
        state = State.search(
            [
                ("name", "ilike", region),
                ("country_id", "=", country_ua.id),
            ],
            limit=1,
        )
        if state:
            return state.id
        state_code = self.get_state_code_for_region(region)
        state = State.search(
            [
                ("code", "=", state_code),
                ("country_id", "=", country_ua.id),
            ],
            limit=1,
        )
        if state:
            return state.id
        try:
            state = State.sudo().create(
                {
                    "name": region,
                    "code": state_code,
                    "country_id": country_ua.id,
                }
            )
            _logger.debug(
                "Created new state for Ukraine: %s (code: %s)", region, state_code
            )
            return state.id
        except Exception as e:
            _logger.debug("Failed to create state for region %s: %s", region, str(e))
            state = State.search(
                [
                    ("code", "=", state_code),
                    ("country_id", "=", country_ua.id),
                ],
                limit=1,
            )
            if state:
                return state.id
            return False

    # pylint: disable=too-many-locals
    def to_address_dict(self, for_js=False):
        self.ensure_one()

        street_with_old = self._format_street_with_old("ua")
        house = self.house_num or ""
        if house and self.house_num_add:
            house = f"{house}{self.house_num_add}"
        if street_with_old and house:
            street = f"{street_with_old} {house}"
        elif street_with_old:
            street = street_with_old
        elif house:
            street = house
        else:
            street = ""

        apt_parts = [
            p for p in [self.apartment_type, self.apartment, self.addition_address] if p
        ]
        street2 = ", ".join([" ".join(apt_parts)]) if apt_parts else ""

        state_id = False
        state_name = ""
        country_ua = self.env.ref("base.ua", raise_if_not_found=False)
        if self.region and country_ua:
            state_id = self.find_or_create_state(self.region, country_ua)
            if state_id:
                state = self.env["res.country.state"].browse(state_id)
                state_name = state.name if state.exists() else ""

        hromada_final = self._format_hromada_with_old("ua")

        area_final = self.area or ""
        area_old = self.area_old or ""
        if area_old and area_old.lower() != area_final.lower():
            area_final = f"{area_final} ({area_old})"

        city_final = self._format_city_with_old("ua")

        if for_js:
            vals = {
                "street": street or "",
                "street2": street2 or "",
                "city": city_final,
                "zip": self.post_index or "",
                "latitude": (self.latitude or self.latitude_settlement or 0),
                "longitude": (self.longitude or self.longitude_settlement or 0),
                "area": area_final,
                "hromada": hromada_final,
                "state_id": [state_id, state_name] if state_id else False,
                "country_id": (
                    [country_ua.id, country_ua.name] if country_ua else False
                ),
                "geodata_address_ua_postal": self.address_ua_postal or "",
                "geodata_address_ua_short": self.address_ua_short or "",
                "geodata_address_western": self.address_western or "",
                "geodata_address_full_ua": self.address_full_ua or "",
                "geodata_address_full_ru": self.address_full_ru or "",
                "geodata_address_full_en": self.address_full_en or "",
                "geodata_address_letter_ua": self.address_letter_ua or "",
                "geodata_address_letter_ru": self.address_letter_ru or "",
                "geodata_address_letter_en": self.address_letter_en or "",
            }
        else:
            vals = {
                "street": street or False,
                "street2": street2 or False,
                "city": city_final or False,
                "zip": self.post_index or False,
                "latitude": (self.latitude or self.latitude_settlement or False),
                "longitude": (self.longitude or self.longitude_settlement or False),
                "area": area_final or False,
                "hromada": hromada_final or False,
                "state_id": state_id,
                "country_id": country_ua.id if country_ua else False,
            }

        return vals

    def to_partner_values(self, for_js=False):
        vals = self.to_address_dict(for_js=for_js)
        if for_js:
            vals["partner_latitude"] = vals.pop("latitude", 0)
            vals["partner_longitude"] = vals.pop("longitude", 0)
        else:
            vals["partner_latitude"] = vals.pop("latitude", False)
            vals["partner_longitude"] = vals.pop("longitude", False)
        return vals
