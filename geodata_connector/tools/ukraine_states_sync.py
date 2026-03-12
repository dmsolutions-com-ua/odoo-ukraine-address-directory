import json
import logging
from os.path import dirname, join

_logger = logging.getLogger(__name__)


class UkraineStatesSync:
    """Utility class for syncing Ukraine states from JSON file"""

    CONFLICTING_PAIRS = {
        "UA30": "UA32",
        "UA32": "UA30",
    }

    @staticmethod
    def load_ukraine_states_data():
        """Load Ukraine states data from JSON file

        Returns:
            dict: Dictionary with Ukraine states data
        """
        json_path = join(
            dirname(dirname(__file__)), "data", "res_country_state_ukraine.json"
        )
        try:
            with open(json_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            _logger.error("Failed to load Ukraine states JSON: %s", str(e))
            raise

    @staticmethod
    def _is_conflicting_pair(code, duplicate_code):
        """Check if two state codes form a conflicting pair.

        Conflicting pairs are states that should not be merged together
        due to similar names but different meanings (e.g., Kyiv city vs
        Kyiv Oblast).

        Args:
            code (str): State code being processed
            duplicate_code (str): Code of potential duplicate

        Returns:
            bool: True if codes form a conflicting pair
        """
        if not duplicate_code:
            return False
        return UkraineStatesSync.CONFLICTING_PAIRS.get(code) == duplicate_code

    @staticmethod
    def _validate_sync_results(env, expected_count):
        """Validate that all expected states were synced.

        Args:
            env: Odoo environment
            expected_count (int): Expected number of states

        Returns:
            list: List of missing state codes (empty if all present)
        """
        try:
            country_ua = env.ref("base.ua")
        except Exception:
            _logger.debug("Cannot validate: Country Ukraine not found")
            return []

        State = env["res.country.state"].sudo()
        existing_states = State.search([("country_id", "=", country_ua.id)])

        existing_codes = {s.code for s in existing_states if s.code}
        _logger.debug(
            "Validation: found %s states in database (expected %s)",
            len(existing_states),
            expected_count,
        )

        data = UkraineStatesSync.load_ukraine_states_data()
        expected_codes = {s["code"] for s in data["states"]}
        missing_codes = expected_codes - existing_codes

        if missing_codes:
            _logger.debug(
                "Missing states after sync: %s", ", ".join(sorted(missing_codes))
            )

        return sorted(missing_codes)

    @staticmethod
    def get_error_result():
        return {"created": 0, "updated": 0, "skipped": 0, "missing": [], "error": True}

    @staticmethod
    def process_existing_state(state, name, code, stats):
        if state.name != name:
            _logger.debug('Updating state %s: "%s" → "%s"', code, state.name, name)
            try:
                state.write({"name": name})
                stats["updated"] += 1
            except Exception as e:
                _logger.debug("Failed to update state %s: %s", code, str(e))
        else:
            stats["skipped"] += 1

    @staticmethod
    def find_duplicate(State, code, name, name_variants, country_id):
        for variant in [name] + name_variants:
            potential_duplicates = State.search(
                [
                    ("name", "ilike", variant),
                    ("country_id", "=", country_id),
                    ("code", "!=", code),
                ]
            )
            for dup in potential_duplicates:
                if UkraineStatesSync._is_conflicting_pair(code, dup.code):
                    _logger.debug(
                        'Skipping conflicting pair: %s ↔ %s (variant: "%s")',
                        code,
                        dup.code,
                        variant,
                    )
                    continue
                return dup, variant
        return None, None

    @staticmethod
    def process_duplicate(duplicate, name, code, matched_variant, stats):
        _logger.debug(
            'Fixing duplicate state id=%s: "%s" (code=%s) → '
            '"%s" (code=%s) [matched variant: "%s"]',
            duplicate.id,
            duplicate.name,
            duplicate.code or "None",
            name,
            code,
            matched_variant,
        )
        try:
            duplicate.write({"code": code, "name": name})
            stats["updated"] += 1
        except Exception as e:
            _logger.debug("Failed to fix duplicate state %s: %s", duplicate.id, str(e))

    @staticmethod
    def create_new_state(State, code, name, country_id, stats):
        _logger.debug('Creating state %s "%s"', code, name)
        try:
            State.create(
                {
                    "code": code,
                    "name": name,
                    "country_id": country_id,
                }
            )
            stats["created"] += 1
        except Exception as e:
            _logger.error('Failed to create state %s "%s": %s', code, name, str(e))

    @staticmethod
    def sync_ukraine_states(env):
        try:
            data = UkraineStatesSync.load_ukraine_states_data()
        except Exception as e:
            _logger.error("Cannot load Ukraine states data: %s", str(e))
            return UkraineStatesSync.get_error_result()

        try:
            country_ua = env.ref("base.ua")
        except Exception as e:
            _logger.error("Country Ukraine (base.ua) not found: %s", str(e))
            return UkraineStatesSync.get_error_result()

        if not country_ua:
            _logger.error("Country Ukraine (base.ua) not found")
            return UkraineStatesSync.get_error_result()

        State = env["res.country.state"].sudo()
        stats = {"created": 0, "updated": 0, "skipped": 0}

        for state_data in data["states"]:
            code = state_data["code"]
            name = state_data["name"]
            name_variants = state_data.get("name_variants", [])

            state = State.search(
                [("code", "=", code), ("country_id", "=", country_ua.id)], limit=1
            )

            if state:
                UkraineStatesSync.process_existing_state(state, name, code, stats)
                continue

            duplicate, matched_variant = UkraineStatesSync.find_duplicate(
                State, code, name, name_variants, country_ua.id
            )

            if duplicate:
                UkraineStatesSync.process_duplicate(
                    duplicate, name, code, matched_variant, stats
                )
                continue

            UkraineStatesSync.create_new_state(State, code, name, country_ua.id, stats)

        missing_codes = UkraineStatesSync._validate_sync_results(
            env, len(data["states"])
        )
        stats["missing"] = missing_codes

        _logger.debug(
            "Ukraine states sync complete: created=%s, updated=%s, "
            "skipped=%s, missing=%s",
            stats["created"],
            stats["updated"],
            stats["skipped"],
            len(missing_codes),
        )

        return stats
