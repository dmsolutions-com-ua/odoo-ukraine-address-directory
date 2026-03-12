import logging

from . import models
from . import tools

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Called after module installation/upgrade.

    Automatically syncs Ukraine administrative regions (oblasts)
    from JSON reference data to res.country.state model.

    Args:
        env: Odoo environment
    """
    from .tools.ukraine_states_sync import UkraineStatesSync

    try:
        _logger.debug("Starting Ukraine states synchronization...")
        stats = UkraineStatesSync.sync_ukraine_states(env)
        _logger.debug(
            "Ukraine states sync complete: " "created=%s, updated=%s, skipped=%s",
            stats["created"],
            stats["updated"],
            stats["skipped"],
        )
    except Exception as e:
        _logger.debug("Failed to sync Ukraine states: %s", str(e))
