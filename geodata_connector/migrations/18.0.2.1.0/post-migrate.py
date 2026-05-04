import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def _build(settlement_type, city, city_old):
    if not city:
        return ""
    base = f"{settlement_type} {city}".strip() if settlement_type else city
    if city_old and city_old.lower() != city.lower():
        base = f"{base} ({city_old})"
    return base


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    addresses = env["geodata.address"].sudo().search(
        ["|", "|", ("city_string", "=", False),
         ("city_string_en", "=", False), ("city_string_ru", "=", False)]
    )
    if not addresses:
        return
    counts = {"ua": 0, "en": 0, "ru": 0}
    for addr in addresses:
        vals = {}
        if not addr.city_string and addr.city:
            vals["city_string"] = _build(
                addr.settlement_type, addr.city, addr.city_old
            )
            counts["ua"] += 1
        if not addr.city_string_en and addr.city_en:
            vals["city_string_en"] = _build(
                addr.settlement_type_en, addr.city_en, addr.city_old_en
            )
            counts["en"] += 1
        if not addr.city_string_ru and addr.city_ru:
            vals["city_string_ru"] = _build(
                addr.settlement_type_ru, addr.city_ru, addr.city_old_ru
            )
            counts["ru"] += 1
        if vals:
            addr.write(vals)
    _logger.info(
        "city_string backfill: ua=%d, en=%d, ru=%d",
        counts["ua"], counts["en"], counts["ru"],
    )
