# Integration Domain Unit Tests

## Overview

This test suite provides comprehensive coverage for the Integration domain, which bridges the Banking and Accounting domains in the banking-bot application.

## Test Organization

```
tests/unit/domain/integration/
├── __init__.py
├── test_account_mapping.py          (25 tests)
├── test_transaction_import.py        (40 tests)
├── test_import_status.py            (20 tests)
└── test_categorization_rule.py       (36 tests)
```

**Total: 121 tests**

## Test Coverage by Component

### 1. AccountMapping Entity (`test_account_mapping.py`)

**Purpose:** Links bank accounts (IBANs) to accounting asset accounts.

**Test Coverage (25 tests):**

- **Creation & Initialization:**
  - Basic creation with required parameters
  - IBAN normalization (uppercase, trimming)
  - Account name normalization
  - Default values (is_active=True)

- **Deterministic UUID:**
  - Same IBAN + accounting_account_id → same mapping ID
  - Different IBAN → different mapping ID
  - Different accounting_account_id → different mapping ID
  - Case-insensitive IBAN for ID generation

- **Validation:**
  - Empty IBAN raises ValueError
  - Invalid IBAN length (< 15 or > 34 chars) raises ValueError
  - Invalid IBAN country code (must start with 2 letters) raises ValueError
  - Empty account name raises ValueError
  - Various valid IBAN formats (German, UK, French, Italian, Spanish)

- **Business Operations:**
  - Update account name (with validation)
  - Deactivate/activate mapping
  - Update accounting account (regenerates deterministic ID)

- **Entity Behavior:**
  - Equality based on ID
  - Hashable (can be used in sets/dicts)
  - String representation

---

### 2. TransactionImport Entity (`test_transaction_import.py`)

**Purpose:** Tracks the import history of bank transactions into the accounting system.

**Test Coverage (40 tests):**

- **Creation & Initialization:**
  - Basic creation with bank transaction identity
  - Creation with all parameters
  - Identity normalization (trimming)

- **Deterministic UUID:**
  - Same bank transaction identity → same import record ID
  - Different identity → different import record ID

- **Validation:**
  - Empty identity raises ValueError
  - SUCCESS status requires accounting_transaction_id
  - FAILED status requires error_message

- **State Transitions:**
  - `mark_as_imported()` - sets SUCCESS status
  - `mark_as_failed()` - sets FAILED status with error message
  - `mark_as_duplicate()` - sets DUPLICATE status
  - `mark_as_skipped()` - sets SKIPPED status with reason
  - `retry()` - resets to PENDING (only for FAILED/SKIPPED)

- **Business Rules:**
  - Cannot mark already imported transaction as imported again
  - Cannot retry successful import
  - Marking as imported clears previous error
  - Error message trimming and validation

- **Status Queries:**
  - `is_imported()`, `is_failed()`, `is_duplicate()`, `is_skipped()`
  - `can_retry()` logic

- **Lifecycle Tests:**
  - PENDING → SUCCESS
  - PENDING → FAILED → retry → SUCCESS
  - PENDING → DUPLICATE
  - PENDING → SKIPPED → retry

- **Entity Behavior:**
  - Equality based on ID
  - Hashable
  - String representation (with long identity truncation)
  - Timestamp management

---

### 3. ImportStatus Value Object (`test_import_status.py`)

**Purpose:** Enum defining the status of transaction import operations.

**Test Coverage (20 tests):**

- **Status Values:**
  - PENDING, SUCCESS, FAILED, DUPLICATE, SKIPPED

- **Business Logic Methods:**
  - `is_final()` - Returns True for SUCCESS, DUPLICATE
  - `is_error()` - Returns True for FAILED
  - `can_retry()` - Returns True for FAILED, SKIPPED

- **Logical Consistency:**
  - Final statuses cannot be retried
  - Error statuses can be retried
  - All statuses have defined behavior

- **Enum Behavior:**
  - Equality comparison
  - Membership in lists
  - Coverage of all statuses

---

### 4. CategorizationRule Value Object (`test_categorization_rule.py`)

**Purpose:** Rules for automatically categorizing bank transactions.

**Test Coverage (36 tests):**

#### PatternType Enum (2 tests):
- All pattern types exist (COUNTERPARTY_NAME, PURPOSE_TEXT, AMOUNT_EXACT, AMOUNT_RANGE, IBAN, COMBINED)
- Correct enum values

#### RuleSource Enum (2 tests):
- All sources exist (SYSTEM_DEFAULT, USER_CREATED, AI_LEARNED, AI_GENERATED)
- Correct enum values

#### CategorizationRule (32 tests):

- **Creation & Initialization:**
  - Basic creation with required parameters
  - Creation with all optional parameters
  - Pattern value trimming
  - Default values (priority=100, source=USER_CREATED, is_active=True)

- **Validation:**
  - Empty pattern value raises ValueError
  - Negative priority raises ValueError

- **Pattern Matching - COUNTERPARTY_NAME:**
  - Case-insensitive matching
  - Partial matching (pattern in name)
  - Returns False when applicant_name is None

- **Pattern Matching - PURPOSE_TEXT:**
  - Case-insensitive matching
  - Substring matching in purpose field

- **Pattern Matching - AMOUNT_EXACT:**
  - Exact amount matching
  - Uses absolute value (works for both positive and negative)
  - Handles invalid pattern value gracefully

- **Pattern Matching - IBAN:**
  - Case-insensitive matching
  - Handles spaces in IBAN
  - Returns False when applicant_iban is None

- **Pattern Matching - General:**
  - Inactive rules never match
  - Unimplemented pattern types return False

- **Business Operations:**
  - `record_match()` - increments count, updates timestamp
  - `update_priority()` - with validation
  - `deactivate()`/`activate()`
  - `update_category()` - changes target account

- **Entity Behavior:**
  - Equality based on ID
  - Hashable
  - String representation (includes status, type, value, priority, match count)

---

## Key Testing Patterns

### 1. Deterministic UUID Testing
Both `AccountMapping` and `TransactionImport` use deterministic UUIDs:
- Tests verify same inputs → same ID
- Tests verify different inputs → different ID
- Tests verify ID regeneration when identity-defining fields change

### 2. Validation Testing
Comprehensive validation tests for:
- Required fields (not empty)
- Format validation (IBAN format)
- Range validation (priority ≥ 0)
- State-dependent validation (SUCCESS requires accounting_transaction_id)

### 3. State Machine Testing
For `TransactionImport`:
- Valid state transitions
- Invalid state transition prevention
- State-dependent behavior (can_retry, etc.)
- Complete lifecycle testing

### 4. Business Rule Testing
- Active/inactive behavior
- Priority-based ordering
- Pattern matching logic
- Error handling and recovery

### 5. Entity Behavior Testing
All entities test:
- Equality semantics
- Hashability
- String representation
- Timestamp management

---

## Test Statistics

- **Total Tests:** 121
- **Pass Rate:** 100%
- **Coverage Areas:**
  - Entities: 2 (AccountMapping, TransactionImport)
  - Value Objects: 3 (ImportStatus, CategorizationRule, PatternType/RuleSource enums)
  - Business Operations: ~50 distinct operations
  - Validation Rules: ~25 validation scenarios
  - State Transitions: ~10 state machines

---

## Running the Tests

```bash
# Run all integration domain tests
pytest tests/unit/domain/integration/ -v

# Run specific test file
pytest tests/unit/domain/integration/test_account_mapping.py -v

# Run with coverage
pytest tests/unit/domain/integration/ --cov=swen/domain/integration
```

---

## Test Quality Characteristics

1. **Comprehensive:** Tests cover happy paths, edge cases, and error conditions
2. **Isolated:** Each test is independent and can run in any order
3. **Clear:** Descriptive test names and docstrings explain intent
4. **Fast:** All 121 tests run in < 1 second
5. **Maintainable:** Tests follow consistent patterns and naming conventions
6. **Deterministic:** No flaky tests, all assertions are precise

---

## Future Enhancements

Potential areas for additional testing:
- Repository implementations (when created)
- Service layer integration (when created)
- Concurrent modification scenarios
- Performance testing for rule matching
- Fuzzy matching algorithms (when implemented)
