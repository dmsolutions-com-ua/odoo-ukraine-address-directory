import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    _logger.info(
        "Migrating geodata_connector to %s: "
        "adding moniker columns to geodata_address",
        version,
    )

    cr.execute("""
        ALTER TABLE geodata_address
        ADD COLUMN IF NOT EXISTS city_moniker VARCHAR,
        ADD COLUMN IF NOT EXISTS street_moniker VARCHAR
    """)
