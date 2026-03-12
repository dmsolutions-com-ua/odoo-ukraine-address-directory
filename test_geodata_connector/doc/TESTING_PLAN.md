# Testing Plan for Geodata Connector Module

**Version**: 1.0
**Date**: 2025-10-02
**Status**: Draft - To be implemented after MVP validation

## Overview

This document outlines the testing strategy for the `geodata_connector` module. Tests should be implemented **after** manual verification of MVP functionality.

## Test Structure

Tests will be located in `tests/` directory with the following structure:
```
tests/
├── __init__.py
├── test_geodata_api_credential.py
├── test_geodata_address.py
├── test_geodata_wizard.py
└── test_res_partner_integration.py
```

## Unit Tests

### test_geodata_api_credential.py

**Purpose**: Test API credential functionality and API response parsing

#### Test Cases:

1. **test_parse_api_response_success**
   - Mock successful API response from Geodata
   - Verify correct parsing of JSON data
   - Check field mapping (Index_ → post_index, Lat_ → latitude, Long_ → longitude)

2. **test_parse_api_response_error**
   - Mock error API response
   - Verify error handling
   - Check error message extraction

3. **test_api_address_search**
   - Mock API call to /api/Address endpoint
   - Verify request parameters (sRequest, sLang)
   - Check response structure

4. **test_api_cities_search**
   - Mock API call to /api/Cities endpoint
   - Verify city search functionality

5. **test_api_headers_geodata**
   - Test `@use_fname('geodata')` decorator
   - Verify proper headers generation (Authorization with Bearer token)

6. **test_action_test_connection**
   - Mock successful connection test
   - Mock failed connection test
   - Verify notification messages

### test_geodata_address.py

**Purpose**: Test geodata.address model functionality

#### Test Cases:

1. **test_create_from_api_response**
   - Provide sample API response data
   - Call `create_from_api_response()` method
   - Verify all fields mapped correctly:
     - Index_ → post_index
     - Lat_ → latitude
     - Long_ → longitude
     - Lat_S → latitude_settlement
     - Long_S → longitude_settlement

2. **test_to_partner_values**
   - Create geodata.address record
   - Call `to_partner_values()` method
   - Verify returned dict contains:
     - street (combination of str_type + street + house_num)
     - street2 (apartment info)
     - city (settlement_type + city)
     - zip (post_index)
     - partner_latitude, partner_longitude

3. **test_state_id_creation**
   - Test with region that doesn't exist in res.country.state
   - Verify new state is created automatically
   - Check state code generation

4. **test_compute_name**
   - Test name computation from address_string
   - Test fallback to city + street
   - Test fallback for empty records

## Integration Tests

### test_geodata_wizard.py

**Purpose**: Test wizard functionality and interaction with API

#### Test Cases:

1. **test_wizard_open_from_partner**
   - Open res.partner form
   - Trigger `action_open_geodata_wizard()`
   - Verify wizard opens with correct context
   - Check partner_id in wizard

2. **test_wizard_default_get**
   - Create partner with existing address data
   - Open wizard
   - Verify search_query pre-filled from partner fields

3. **test_wizard_search**
   - Mock API response with address list
   - Call `action_search()` with query
   - Verify address_result_ids populated
   - Check geodata.address records created

4. **test_wizard_apply_to_partner**
   - Select address from results
   - Call `action_select_and_apply()`
   - Verify partner fields updated
   - Check geodata_address_id link

5. **test_wizard_empty_results**
   - Mock empty API response
   - Verify appropriate error message

### test_res_partner_integration.py

**Purpose**: Test res.partner model integration

#### Test Cases:

1. **test_partner_action_open_geodata_wizard**
   - Create partner
   - Call `action_open_geodata_wizard()`
   - Verify ir.actions.act_window returned
   - Check target='new' (wizard mode)

2. **test_partner_has_geodata_address**
   - Create partner without geodata_address_id
   - Verify has_geodata_address = False
   - Link geodata_address
   - Verify has_geodata_address = True

3. **test_geodata_address_persistence**
   - Create partner with geodata address
   - Save and reload partner
   - Verify geodata_address_id preserved

4. **test_apply_geodata_address**
   - Create geodata.address
   - Call partner.apply_geodata_address()
   - Verify all fields populated correctly
   - Check coordinates set

## End-to-End Tests (Manual for MVP)

### E2E Test Scenarios

#### Scenario 1: New Partner Address

1. Navigate to Contacts
2. Click "Create"
3. Enter partner name
4. Click "🌍 Address Wizard" button
5. **Expected**: Wizard opens with empty/default fields
6. Select API credential (if multiple)
7. Enter search query: "Київ Хрещатик 1"
8. Click "Search"
9. **Expected**: List of addresses appears within 1 second
10. Click "Select" on desired address
11. **Expected**: Address highlighted, selected_address_id set
12. Click "Apply Selected"
13. **Expected**:
    - Wizard closes
    - Partner form shows populated fields (street, city, zip)
    - Coordinates filled (partner_latitude, partner_longitude)
14. Save partner
15. **Expected**: Partner saved successfully with geodata link

#### Scenario 2: Update Existing Partner Address

1. Open existing partner with address
2. Click "🌍 Address Wizard"
3. **Expected**: search_query pre-filled with current address
4. Modify search query
5. Search and select new address
6. Apply
7. **Expected**: Partner fields updated with new address

#### Scenario 3: Multi-language Support

1. Change UI language to Ukrainian
2. Open wizard
3. **Expected**: All labels in Ukrainian
4. Search with sLang=uk_UA
5. **Expected**: Results in Ukrainian
6. Change language selection to Russian
7. Search again
8. **Expected**: Results in Russian

## Performance Tests

### Test Cases:

1. **test_api_response_time**
   - Execute 10 consecutive API calls
   - Measure response time for each
   - **Requirement**: 95th percentile < 1 second

2. **test_wizard_search_performance**
   - Open wizard
   - Execute search
   - Measure time from click to results display
   - **Requirement**: < 2 seconds total

3. **test_bulk_address_creation**
   - Mock 100 API responses
   - Create geodata.address records
   - **Requirement**: < 5 seconds for 100 records

## Test Execution Commands

```bash
# Run all tests for module
cd /home/vovik/odoo_dev/geodata18
odoo-helper test -m geodata_connector

# Run with coverage
odoo-helper test --coverage -m geodata_connector

# Generate HTML coverage report
odoo-helper test --coverage-html -m geodata_connector

# Run specific test file
odoo-helper test -m geodata_connector --test-file=tests/test_geodata_wizard.py
```

## Mock Data for Tests

### Sample API Response (Address Search)

```python
MOCK_API_RESPONSE = [
    {
        'Id': 12345,
        'AddressString': 'м. Київ, вул. Хрещатик, 1',
        'Index_': '01001',
        'Region': 'Київська',
        'City': 'Київ',
        'SettlementType': 'місто',
        'Street': 'Хрещатик',
        'StrType': 'вул.',
        'HouseNum': '1',
        'Lat_': 50.4501,
        'Long_': 30.5234,
        'KATO': '8000000000',
    }
]
```

## Test Coverage Goals

- **Overall Coverage**: > 80%
- **Critical Paths**: 100%
  - API request methods
  - Wizard apply functionality
  - Field mapping (geodata.address → res.partner)
- **Models**: > 85%
- **Wizards**: > 90%

## Testing Timeline

1. **After MVP Validation** (current milestone):
   - Manual E2E testing
   - Functional verification
   - User acceptance

2. **Phase 2** (after MVP approved):
   - Implement unit tests
   - Implement integration tests
   - Achieve 80% coverage

3. **Phase 3** (before production):
   - Performance testing
   - Stress testing
   - Security testing

## Notes

- Tests use Odoo's `TransactionCase` class
- Mock external API calls using `unittest.mock.patch`
- Use demo data where possible
- Isolate database changes in transactions
- Clean up test data after each test

## Checklist Before Production

- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] Coverage > 80%
- [ ] Manual E2E scenarios verified
- [ ] Performance requirements met (<1s API response)
- [ ] Multi-language tested (UK/RU)
- [ ] Multi-company tested (if applicable)
- [ ] Error handling verified
- [ ] Security review completed
- [ ] Documentation updated
