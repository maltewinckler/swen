# Integration Tests

This directory contains integration tests that connect to a real bank using the FinTS protocol.

WARNING: **WARNING:** These tests require real bank credentials and are NOT run by default.

## Quick Start

### 1. Set Up Credentials

```bash
# Copy the example .env file (in repository root)
cp .env.example .env

# Edit .env and fill in your credentials
nano .env
```

Your `.env` should look like:
```bash
RUN_INTEGRATION_TESTS=true
FINTS_BLZ=50031000
FINTS_USERNAME=your_username
FINTS_PIN=your_pin
FINTS_ENDPOINT=https://banking.triodos.de/fints/servlet
```

### 2. Run Tests

```bash
# Run all integration tests
poetry run pytest tests/integration/ -v

# Run only non-TAN tests (recommended, faster)
poetry run pytest tests/integration/ -v -m "not tan"

# Run specific test class
poetry run pytest tests/integration/test_fints_integration.py::TestRealBankConnection -v
```

## Test Categories

### Non-TAN Tests (Safe, Fast)

These tests typically don't require TAN approval:

**Connection Tests:**
- `test_connect_to_bank` - Verify authentication works
- `test_disconnect` - Verify clean disconnect
- `test_multiple_connect_disconnect_cycles` - Connection stability
- `test_connection_with_invalid_credentials_fails` - Error handling

**Account Tests:**
- `test_fetch_accounts` - List all accounts
- `test_accounts_have_valid_iban` - IBAN format validation
- `test_accounts_have_consistent_blz` - BLZ consistency
- `test_accounts_have_currency` - Currency field present
- `test_account_holder_name_present` - Owner information

**Transaction Tests (30 days):**
- `test_fetch_recent_transactions` - Fetch last 30 days
- `test_transactions_have_required_fields` - Data completeness
- `test_transaction_amounts_are_decimal` - Proper amount types
- `test_transaction_dates_are_ordered` - Chronological order
- `test_fetch_transactions_with_date_filter` - Date filtering
- `test_fetch_transactions_for_all_accounts` - Multi-account support

### WARNING: TAN Tests (Manual Only)

These tests MAY require TAN approval (marked with `@pytest.mark.tan`):

- `test_long_history_triggers_tan` - Fetch 200+ days (requires TAN)

**Note:** TAN tests are skipped by default and require manual approval via your banking app.

## What Gets Tested

### Connection & Authentication
- Connect to real bank with credentials
- Disconnect cleanly
- Handle invalid credentials gracefully

### Account Fetching
- List all accounts
- Validate IBAN format (DE + 22 chars)
- Verify BLZ consistency
- Check currency and owner fields

### Transaction Fetching
- Fetch recent transactions (30 days)
- Validate transaction fields (dates, amounts, purpose)
- Verify Decimal precision (2 decimal places)
- Check chronological ordering
- Test date filtering

### NOT Tested (By Design)
- SEPA transfers (read-only policy)
- TAN automation (impossible for app-based TAN)
- Specific account balances (user-specific data)
- Exact transaction counts (varies over time)

## Safety Features

###  Security
1. **No automatic execution** - Requires `RUN_INTEGRATION_TESTS=1`
2. **Credentials in .env** - Never in code, git-ignored
3. **Read-only operations** - No transfers or modifications
4. **No sensitive assertions** - No hardcoded account numbers or amounts

### Credential Management
- `.env` file is in `.gitignore`
- Credentials loaded via `python-dotenv`
- Shared with example scripts (consistent configuration)
- BLZ validation (8 digits, numeric only)

### ⏭️ Graceful Skipping
Tests automatically skip if:
- `RUN_INTEGRATION_TESTS` not set
- Credentials missing or invalid
- No accounts available
- No transactions in date range
- Connection fails

## When to Run

### **Run Integration Tests:**
- Before major releases
- After FinTS adapter changes
- After python-fints library updates
- Monthly smoke test
- When debugging bank connection issues

### **Don't Run:**
- On every commit (too slow)
- In CI/CD pipeline (unless you have test bank credentials)
- During development (use unit tests instead)

## Troubleshooting

### Tests Skip with "Integration tests disabled"

**Problem:** `RUN_INTEGRATION_TESTS` not set

**Solution:**
```bash
# In .env file
RUN_INTEGRATION_TESTS=true

# Or set environment variable
export RUN_INTEGRATION_TESTS=1
poetry run pytest tests/integration/ -v
```

### Tests Skip with "Missing credentials"

**Problem:** `.env` file not found or incomplete

**Solution:**
```bash
# Check .env exists in repository root
ls -la .env

# If not, copy from example
cp .env.example .env

# Edit and fill in all credentials
nano .env
```

### Connection Fails

**Problem:** Invalid credentials or wrong endpoint

**Solutions:**
1. Verify BLZ is correct (8 digits)
2. Check username/PIN are correct
3. Verify FinTS endpoint URL
4. Ensure online banking is enabled
5. Check if bank is accessible (not maintenance window)

### TAN Required Unexpectedly

**Problem:** Test triggers TAN even though it shouldn't

**Solutions:**
1. Reduce date range (use 7 days instead of 30)
2. Wait a few minutes (bank cooldown period)
3. Skip TAN tests: `pytest -m "not tan"`
4. Some banks require TAN for first-time access

### Rate Limiting

**Problem:** Bank blocks after too many requests

**Solution:**
1. Wait 2-5 minutes before retrying
2. Use `scope="module"` fixtures (single connection)
3. Don't run tests too frequently

## Configuration

### Module-Scoped Fixtures

The `connected_adapter` fixture uses `scope="module"` to:
- Reuse connection across all tests (faster)
- Avoid rate limiting
- Single TAN approval for all tests

### Environment Variables

All loaded from repository root `.env`:

```bash
# Required
RUN_INTEGRATION_TESTS=true     # Enable tests
FINTS_BLZ=50031000             # Your bank's BLZ
FINTS_USERNAME=username        # Online banking username
FINTS_PIN=pin                  # Online banking PIN
FINTS_ENDPOINT=https://...     # FinTS server URL
```

### Test Markers

```bash
# Run only integration tests
pytest -m integration

# Skip integration tests
pytest -m "not integration"

# Skip TAN tests
pytest -m "not tan"

# Run only TAN tests (manual)
pytest -m tan
```

## Best Practices

### 1. **Use Short Date Ranges**
```python
# Good - 30 days or less (no TAN)
start_date = date.today() - timedelta(days=30)

# Bad - Long history (requires TAN)
start_date = date.today() - timedelta(days=200)
```

### 2. **Skip Gracefully**
```python
# Good - Skip if no data
if not accounts:
    pytest.skip("No accounts available")

# Bad - Fail if no data
assert len(accounts) > 0  # Might be empty!
```

### 3. **Don't Assert Specific Data**
```python
# Good - Check structure
assert tx.amount is not None
assert isinstance(tx.amount, Decimal)

# Bad - Hardcode values
assert tx.amount == Decimal("123.45")  # Changes over time!
```

### 4. **Always Clean Up**
```python
# Good - Use try/finally
try:
    await adapter.connect(credentials)
    # ... tests ...
finally:
    await adapter.disconnect()
```

## Example Output

### Successful Run
```bash
$ poetry run pytest tests/integration/ -v -m "not tan"

tests/integration/test_fints_integration.py::TestRealBankConnection::test_connect_to_bank PASSED
tests/integration/test_fints_integration.py::TestRealBankConnection::test_disconnect PASSED
tests/integration/test_fints_integration.py::TestRealAccountFetching::test_fetch_accounts PASSED
tests/integration/test_fints_integration.py::TestRealAccountFetching::test_accounts_have_valid_iban PASSED
tests/integration/test_fints_integration.py::TestRealTransactionFetching::test_fetch_recent_transactions PASSED

==================== 12 passed in 15.23s ====================
```

### Skipped (No Credentials)
```bash
$ pytest tests/integration/ -v

tests/integration/test_fints_integration.py::TestRealBankConnection::test_connect_to_bank SKIPPED
Reason: Integration tests disabled. Enable by setting RUN_INTEGRATION_TESTS=1 in .env

==================== 12 skipped in 0.05s ====================
```

## Related Documentation

- **Testing Strategy:** `docs/TESTING_STRATEGY.md`
- **Testing Quick Start:** `docs/TESTING_QUICK_START.md`
- **TAN Handling:** `docs/TAN_HANDLING.md`
- **Root .env Example:** `.env.example`

## Support

For issues or questions:
1. Check `docs/TROUBLESHOOTING_TAN.md`
2. Verify credentials in `.env`
3. Try with shorter date range
4. Check bank's online banking status
5. Review test output for specific error messages
