# Integration Tests for Persistence Layer

## Quick Start

```bash
# Run all integration tests
pytest tests/integration/persistence/ -v

# Run with coverage
pytest tests/integration/persistence/ --cov=swen/infrastructure/persistence -v
```

## Test Status

**9 passing tests** (0.43s)
- Account persistence (2/3 tests)
- Transaction persistence (4/4 tests)
- Complex scenarios (3/4 tests)

⏭️ **2 skipped tests** (features not yet implemented)
- `test_update_account_balance_after_sync` - needs `update_balance()` method
- `test_last_sync_tracking` - needs `last_sync_at` field in domain model

## Test Coverage

### TestAccountPersistenceIntegration
- `test_save_and_retrieve_fints_account` - Complete account lifecycle
- ⏭️ `test_update_account_balance_after_sync` - Balance update functionality
- `test_multiple_accounts_for_user` - Multi-account scenarios

### TestTransactionPersistenceIntegration
- `test_save_transactions_from_fints` - Basic transaction persistence
- `test_incremental_transaction_sync` - Incremental sync with overlapping data
- `test_duplicate_transaction_prevention` - Deterministic UUID deduplication
- `test_transactions_without_bank_reference` - Handling missing optional fields

### TestComplexPersistenceScenarios
- `test_complete_sync_workflow` - Full FinTS sync workflow (accounts + transactions)
- `test_account_deletion_cascades_to_transactions` - Cascade delete behavior
- `test_date_range_queries` - Date-based filtering
- ⏭️ `test_last_sync_tracking` - Sync timestamp tracking

## Key Features Tested

### Data Integrity
- BLZ extraction from IBAN for German accounts
- Field mapping between database and domain models (owner_name ↔ account_holder)
- Timezone handling (SQLite limitations documented)
- Optional field handling (bank_reference, balance_date, etc.)

### Business Logic
- Deterministic UUID generation for transaction deduplication
- Identity hash computation for transactions
- Incremental sync with duplicate prevention
- Cascade deletes (account → transactions)

### FinTS Integration
- Realistic FinTS-like account data structures
- Realistic FinTS-like transaction data structures
- Complete sync workflow simulation
- Handling of incomplete/missing data from FinTS

## Helper Functions

### `create_fints_like_account(**kwargs)`
Creates a realistic bank account as returned by FinTS:
```python
account = create_fints_like_account(
    iban="DE89370400440532013000",
    account_holder="Max Mustermann",
    bank_name="Commerzbank",
    balance=Decimal("1234.56"),
)
```

### `create_fints_like_transaction(**kwargs)`
Creates a realistic bank transaction as returned by FinTS:
```python
transaction = create_fints_like_transaction(
    booking_date=date(2025, 10, 1),
    amount=Decimal("-50.00"),
    purpose="REWE Sagt Danke",
    bank_reference="REF-123456",
)
```

## Fixtures

### `integration_engine` (module scope)
- Connects to PostgreSQL test database (same as production)
- Reused across all tests in the module for performance
- Cleaned up after all tests complete

### `integration_session` (function scope)
- Fresh database session for each test
- Creates all tables before test
- Drops all tables after test
- Ensures test isolation

## Issues Fixed by Integration Tests

1. **BLZ Validation Error**
   - Problem: Repository set `blz=""` but domain requires 8 characters
   - Fix: Extract BLZ from IBAN positions 4-12

2. **Timezone Handling**
   - Problem: PostgreSQL requires timezone-aware datetimes with `DateTime(timezone=True)`
   - Fix: All datetime columns now use `DateTime(timezone=True)`

3. **Field Mapping Consistency**
   - Verified: `owner_name` (DB) ↔ `account_holder` (domain) works end-to-end

4. **UUID Type Handling**
   - Problem: PostgreSQL uses native UUID type, not strings
   - Fix: All `user_id` columns use `Uuid` type, removed `.hex` conversions

## Documentation

See **[INTEGRATION_TESTING_GUIDE.md](./INTEGRATION_TESTING_GUIDE.md)** for:
- Detailed explanation of what to pay attention to
- Unit tests vs integration tests comparison
- Common pitfalls and how to avoid them
- Best practices for integration testing
- Troubleshooting guide

## Next Steps

### Implement Skipped Features
1. Add `update_balance()` method to `BankAccountRepositorySQLAlchemy`
2. Expose `last_sync_at` in domain model or create separate sync tracking

### Additional Test Scenarios
- Multi-user isolation (verify users can't see each other's data)
- Concurrent access (multiple processes syncing same account)
- Large dataset performance (1000+ transactions)
- Error recovery (network failures, partial syncs)

### Database Testing
Tests now use PostgreSQL by default (same as production):
- Set `TEST_USE_SQLITE=1` to use SQLite for faster tests
- PostgreSQL catches timezone and type issues that SQLite ignores
- Foreign key constraints are strictly enforced
