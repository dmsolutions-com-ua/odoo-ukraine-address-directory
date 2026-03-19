учше# Architecture - odoo-ukraine-address-directory

## Dependency Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      geodata_online                         │
│            (meta-module, App Store bundle)                   │
│         depends: all geodata_* modules below                │
└──┬──────────┬──────────┬──────────┬──────────┬──────────────┘
   │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼
┌────────┐┌────────┐┌────────┐┌────────┐┌──────────┐
│geodata ││geodata ││geodata ││geodata ││geodata   │
│_company││_crm    ││_hr     ││_lunch  ││_contact  │
│        ││        ││        ││        ││          │
│res.    ││crm.    ││hr.     ││lunch.  ││res.      │
│company ││lead    ││employee││supplier││partner   │
└──┬──┬──┘└──┬──┬──┘└──┬──┬──┘└──┬──┬──┘│+ wizard  │
   │  │      │  │      │  │      │  │   └──┬──┬────┘
   │  │      │  │      │  │      │  │      │  │
   │  └──┐   │  └──┐   │  └──┐   │ └──┐   │  │
   │     │   │     │   │     │   │    │   │  │
   │     ▼   │     ▼   │     ▼   │    ▼   │  │
   │  ┌──────────────────────────────────┐│  │
   │  │     kw_widget_autocomplete       ││  │
   │  │     (autocomplete UI widget)     ││  │
   │  └──────────────────────────────────┘│  │
   │                                      │  │
   ▼                                      ▼  │
┌─────────────────────────────────────────────┤
│            geodata_connector                │
│                (core)                       │
│                                             │
│  geodata.address        geodata.api.credential
│  geodata.address.mixin  geodata.api.connector
│  base.geocoder                              │
└──────────┬──────────────────────────────────┘
           │                          ▲
           ▼                          │
┌──────────────────┐    ┌─────────────┴──────────┐
│ kw_api_connector │    │ test_geodata_connector  │
│ (API framework)  │    │ (tests, mock API, tour) │
└──────────────────┘    │                         │
                        │ geodata.api.response.mock
                        │ geodata.api.credential.tour
                        └─────────────────────────┘

External Odoo modules:
  base, base_geolocalize, contacts, crm, hr, lunch
```

## Module Layers

| Layer | Module | Purpose |
|-------|--------|---------|
| **4 - App** | `geodata_online` | Meta-module for Odoo App Store, bundles everything |
| **3 - Integrations** | `geodata_company`, `geodata_crm`, `geodata_hr`, `geodata_lunch` | Add autocomplete to specific Odoo forms |
| **2 - UI** | `geodata_contact` | Address selection wizard, JS logic, `res.partner` extension |
| **1 - Core** | `geodata_connector` | API integration, address models, OAuth 2.0, geocoding |
| **0 - Framework** | `kw_api_connector`, `kw_widget_autocomplete` | External KitWorks libraries |
| **T - Tests** | `test_geodata_connector` | Mock API, demo data, JS tour tests |

## Models (13 total)

```
geodata_connector:
  ├── geodata.address           — address data storage
  ├── geodata.address.mixin     — abstract model (shared logic)
  ├── geodata.api.connector     — ← kw.api.connector (API endpoints)
  ├── geodata.api.credential    — ← kw.api.credential (OAuth tokens)
  └── base.geocoder             — abstract (geolocation provider)

geodata_contact:
  ├── res.partner               — extended with address fields
  ├── geodata.address.wizard    — TransientModel (address search)
  └── geodata.address.wizard.result — TransientModel (search results)

Integration modules (1 model each):
  crm.lead, res.company, hr.employee, lunch.supplier

test_geodata_connector:
  ├── geodata.api.response.mock    — mock API response storage
  └── geodata.api.credential.tour  — mock credentials for JS tour
```

## Module Details

### geodata_connector (v18.0.2.0.0)
**Core API integration module**

- OAuth 2.0 Resource Owner Password Credentials flow
- Automatic token refresh on 401 errors
- Address normalization and validation
- Geocoding provider for `base_geolocalize`
- Ukraine state/region reference data (JSON)
- Post-init hook for initial setup

### geodata_contact (v18.0.2.0.0)
**Contact form integration**

- Autocomplete widgets for street, city, area, hromada fields
- Address selection wizard with search results
- JS frontend logic for field interactions
- Ukrainian translations (uk.po)

### geodata_crm (v18.0.1.0.0)
**CRM lead address autocomplete**

- Extends `crm.lead` form with geodata autocomplete fields

### geodata_company (v18.0.1.0.0)
**Company address autocomplete**

- Extends `res.company` form with geodata autocomplete fields

### geodata_hr (v18.0.1.0.0)
**HR employee address autocomplete**

- Extends `hr.employee` form with geodata autocomplete fields

### geodata_lunch (v18.0.1.0.0)
**Lunch supplier address autocomplete**

- Extends `lunch.supplier` form with geodata autocomplete fields

### geodata_online (v18.0.1.0.0)
**Meta-module (App Store bundle)**

- Installs all geodata modules as a single application
- Contains SEO keywords in summary for Odoo App Store visibility
- Additional `res.company` view customizations

### test_geodata_connector (v18.0.1.0.0)
**Testing infrastructure**

- Mock API response model for offline testing
- Tour credential model for JS browser tests
- Demo data (API credentials, address records)
- JS tour tests for autocomplete workflow
