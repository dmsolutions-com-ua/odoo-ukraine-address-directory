import logging

_logger = logging.getLogger(__name__)

_STRIP_OLD = r"\s*\([^()]*\)\s*$"
_HAS_OLD = r"\([^()]*\)\s*$"


def _strip(cr, column):
    cr.execute(
        f"""
        UPDATE geodata_address
           SET {column} = TRIM(REGEXP_REPLACE({column}, %s, ''))
         WHERE {column} ~ %s
        """,
        (_STRIP_OLD, _HAS_OLD),
    )
    return cr.rowcount


def migrate(cr, version):
    if not version:
        return
    ua = _strip(cr, "city_string")
    en = _strip(cr, "city_string_en")
    ru = _strip(cr, "city_string_ru")
    _logger.info(
        "city_string old-name strip: ua=%d, en=%d, ru=%d", ua, en, ru,
    )
