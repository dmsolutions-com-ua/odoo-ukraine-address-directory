import json
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class GeodataApiResponseMock(models.Model):
    _name = "geodata.api.response.mock"
    _description = "Geodata API Response Mock Data"
    _order = "create_date desc"

    name = fields.Char(
        compute="_compute_name",
        store=True,
        help="Display name based on request",
    )
    request_query = fields.Char(
        required=True,
        index=True,
        help="Search query sent to API",
    )
    request_lang = fields.Char(
        string="Request Language",
        default="uk_UA",
        help="Language parameter of request",
    )
    request_params = fields.Text(
        string="Request Parameters (JSON)",
        help="Full request parameters as JSON",
    )
    response_data = fields.Text(
        string="Response Data (JSON)",
        required=True,
        help="API response as JSON",
    )
    response_count = fields.Integer(
        compute="_compute_response_count",
        store=True,
        help="Number of results in response",
    )
    use_in_tests = fields.Boolean(
        string="Use in Tests",
        default=True,
        help="Use this response in mock tests",
    )
    active = fields.Boolean(
        default=True,
        help="Set to false to exclude from mock tests",
    )

    @api.depends("request_query", "request_lang")
    def _compute_name(self):
        for record in self:
            if record.request_query:
                record.name = f"{record.request_query} ({record.request_lang})"
            else:
                record.name = "Mock Response"

    @api.depends("response_data")
    def _compute_response_count(self):
        for record in self:
            if record.response_data:
                try:
                    data = json.loads(record.response_data)
                    if isinstance(data, list):
                        record.response_count = len(data)
                    else:
                        record.response_count = 1
                except Exception:
                    record.response_count = 0
            else:
                record.response_count = 0

    @api.model
    def save_api_response(
        self, request_query, request_lang, request_params, response_data
    ):
        if not self.env.context.get("save_geodata_mock", False):
            return False

        existing = self.search(
            [
                ("request_query", "=", request_query),
                ("request_lang", "=", request_lang),
            ],
            limit=1,
        )

        vals = {
            "request_query": request_query,
            "request_lang": request_lang,
            "request_params": (json.dumps(request_params) if request_params else False),
            "response_data": (
                json.dumps(response_data)
                if not isinstance(response_data, str)
                else response_data
            ),
        }

        if existing:
            existing.write(vals)
            _logger.debug("Updated mock response for query: %s", request_query)
            return existing

        mock = self.create(vals)
        _logger.debug("Saved new mock response for query: %s", request_query)
        return mock

    @api.model
    def get_mock_response(self, request_query, request_lang="uk_UA"):
        mock = self.search(
            [
                ("request_query", "=", request_query),
                ("request_lang", "=", request_lang),
                ("use_in_tests", "=", True),
                ("active", "=", True),
            ],
            limit=1,
        )

        if mock and mock.response_data:
            try:
                return json.loads(mock.response_data)
            except Exception as e:
                _logger.error("Failed to parse mock response: %s", e)
                return None
        return None
