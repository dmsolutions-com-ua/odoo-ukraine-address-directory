import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    _logger.info(
        "Migrating geodata_contact to %s: "
        "copying monikers from res_partner to geodata_address",
        version,
    )

    cr.execute("""
        UPDATE geodata_address ga
        SET city_moniker = p.geodata_city_moniker,
            street_moniker = p.geodata_street_moniker
        FROM res_partner p
        WHERE p.geodata_address_id = ga.id
        AND (p.geodata_city_moniker IS NOT NULL
             OR p.geodata_street_moniker IS NOT NULL)
    """)

    _logger.info("Migrated %d geodata_address records", cr.rowcount)
