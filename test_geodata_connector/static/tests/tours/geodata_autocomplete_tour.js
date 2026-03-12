/** @odoo-module **/

import { registry } from "@web/core/registry";

registry
    .category("web_tour.tours")
    .add("geodata_autocomplete_city_street_tour", {
        url: "/odoo/contacts/new",
        steps: () => [
            {
                trigger: 'div[name="name"] input',
                run: "edit Test Geodata Tour Partner",
            },
            {
                trigger: 'div[name="city"] input',
                run: "edit Київ",
            },
            {
                trigger:
                    '.o-autocomplete--dropdown-item:contains("місто Київ")',
                run: "click",
            },
            {
                trigger: 'div[name="street"] input',
                run: "edit Лук",
            },
            {
                trigger:
                    ".o-autocomplete--dropdown-item"
                    + ":contains(\"Лук'яненка\")",
                run: "click",
            },
            {
                trigger: '.o_form_button_save',
                run: "click",
            },
            {
                trigger: '.o_form_view:not(.o_form_editable)',
            },
            {
                trigger: 'div[name="city"]',
                run() {
                    const input = this.anchor.querySelector("input");
                    const val = input
                        ? input.value
                        : this.anchor.textContent;
                    if (!val || !val.includes("Київ")) {
                        throw new Error(
                            "City was cleared after street: " + val
                        );
                    }
                },
            },
        ],
    });
