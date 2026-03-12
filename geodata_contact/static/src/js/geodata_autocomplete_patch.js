/** @odoo-module **/

import { KwAutocompleteField } from
    "@kw_widget_autocomplete/js/kw_autocomplete_field";
import { patch } from "@web/core/utils/patch";

const GEODATA_METHODS = [
    "apply_address_to_partner",
    "apply_geodata_address",
];

patch(KwAutocompleteField.prototype, {
    _isGeodataMethod() {
        return GEODATA_METHODS.includes(this.props.onSelectMethod);
    },
    async onSelect(option) {
        if (this._isGeodataMethod() && option.data) {
            const addrField = this.props.record.data.geodata_address_id;
            if (addrField) {
                let addrId = false;
                if (Array.isArray(addrField)) {
                    addrId = addrField[0];
                } else if (typeof addrField === "object" && addrField.id) {
                    addrId = addrField.id;
                } else if (typeof addrField === "number") {
                    addrId = addrField;
                }
                if (addrId) {
                    option.data._geodata_address_id = addrId;
                }
            }
        }
        await super.onSelect(option);
        if (this._isGeodataMethod()) {
            if ('geodata_autocomplete_active' in this.props.record.data) {
                await this.props.record.update({
                    geodata_autocomplete_active: false,
                });
            }
        }
    },
});
