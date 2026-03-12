import logging

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class GeoCoder(models.AbstractModel):
    _inherit = "base.geocoder"

    @staticmethod
    def _validate_coordinates(lat, lon, strict_ukraine=False):
        try:
            lat, lon = float(lat), float(lon)
        except (TypeError, ValueError):
            return False

        if strict_ukraine:
            # Approximate bounds for Ukraine
            # Lat: 44.3° to 52.4°, Lon: 22.1° to 40.2°
            if not (44.0 <= lat <= 52.5 and 22.0 <= lon <= 40.5):
                return False

        return all([-90 <= lat <= 90, -180 <= lon <= 180, (lat != 0 or lon != 0)])

    def _call_geodata(self, addr, **kw):
        if not addr:
            return None

        credential = self.env["geodata.api.credential"].get_credential()

        if not credential:
            raise UserError(
                _(
                    "No active Geodata API credential found. "
                    "Please configure Geodata API credentials in Settings."
                )
            )

        result = credential.api_full_address(sRequest=addr, sLang="uk_UA")

        if not result:
            return None

        api_data = result[0] if isinstance(result, list) else result

        latitude, longitude = api_data.get("Lat_"), api_data.get("Long_")

        if not self._validate_coordinates(latitude, longitude):
            return None

        geodata_address = self.env["geodata.address"].search(
            [("geodata_id", "=", api_data.get("Id"))], limit=1
        )

        if not geodata_address:
            geodata_address = self.env["geodata.address"].create_from_api_response(
                api_data
            )

        return (float(latitude), float(longitude))

    @api.model
    def _geo_query_address_geodata(
        self, street=None, zip_code=None, city=None, state=None, country=None
    ):
        address_parts = []

        if state:
            state_name = state if isinstance(state, str) else state.name
            address_parts.append(state_name)

        if city:
            address_parts.append(city)

        if street:
            address_parts.append(street)

        if zip_code:
            address_parts.append(zip_code)

        return ", ".join(filter(None, address_parts))
