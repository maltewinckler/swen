# Test Agent Prompt: Run Complete Test Suite

You are a test automation agent. Your task is to run the **complete** SWEN test suite including all integration tests and external tests with real bank connections.

---

## Instructions

### Step 1: Set Up Docker/Podman Socket

**If using Podman:**
```bash
export DOCKER_HOST="unix:///run/user/$(id -u)/podman/podman.sock"
```

**If using Docker:**
No action needed - ensure Docker daemon is running.

---

### Step 2: Load Credentials from `.env`

Load all environment variables from the `.env` file in the repository root:

```bash
set -a && source .env && set +a
```

This will load:
- `RUN_INTEGRATION` - Enable integration tests
- `RUN_EXTERNAL` - Enable external bank connection tests
- `FINTS_BLZ` - Bank identifier (BLZ)
- `FINTS_USERNAME` - Online banking username
- `FINTS_PIN` - Online banking PIN
- `FINTS_ENDPOINT` - FinTS endpoint URL
- `FINTS_PRODUCT_ID` - Registered FinTS product ID
- `FINTS_TAN_METHOD` - TAN method (e.g., "946" for push-TAN)
- `GATEWAY_API_KEY` - Geldstrom gateway API key

---

### Step 3: Verify Credentials Are Loaded

```bash
echo "RUN_INTEGRATION=$RUN_INTEGRATION"
echo "RUN_EXTERNAL=$RUN_EXTERNAL"
echo "FINTS_BLZ=${FINTS_BLZ:-NOT SET}"
echo "FINTS_USERNAME=${FINTS_USERNAME:-NOT SET}"
echo "FINTS_ENDPOINT=${FINTS_ENDPOINT:-NOT SET}"
```

All values should be populated. If any are "NOT SET", check the `.env` file.

---

### Step 4: Run Backend Tests

```bash
uv run --package swen-backend pytest services/backend/tests/ -v --tb=short
```

**Expected output:**
- ~1,485 tests passed
- ~7 tests skipped (TAN polling and password reset tests)
- Duration: ~5 minutes

---

### Step 5: Run Frontend Tests

```bash
cd services/frontend && npm run test
```

**Expected output:**
- 388 tests passed across 22 test files
- Duration: ~15 seconds

---

### Step 6: Run ML Service Tests

```bash
uv run --package swen-ml pytest services/ml/tests/ -v
```

**Expected output:**
- 2 tests passed
- Duration: ~5 seconds

---

## Success Criteria

| Test Suite | Expected | Acceptable |
|------------|----------|------------|
| Backend | 1,485 passed, 7 skipped | No failures |
| Frontend | 388 passed | No failures |
| ML Service | 2 passed | No failures |

**Total: ~1,875 tests passing**

---

## Troubleshooting

### Docker Socket Error
```
Error: ('Connection aborted.', FileNotFoundError(2, 'No such file or directory'))
```
→ Set `DOCKER_HOST` as shown in Step 1

### Tests Skipped
If many tests show as "SKIPPED", verify:
1. `RUN_INTEGRATION=true` is set
2. `RUN_EXTERNAL=true` is set
3. All `FINTS_*` variables are populated

### Bank Connection Failures
If external tests fail:
1. Verify credentials in `.env` are correct
2. Check `FINTS_BLZ` is exactly 8 digits
3. Verify `FINTS_ENDPOINT` URL is reachable
4. Ensure `FINTS_TAN_METHOD` is set (try "946")

---

## Report Format

After running all tests, report results in this format:

```
## Test Results Summary

### Backend Tests
- Passed: X
- Skipped: Y (reason: ...)
- Failed: Z

### Frontend Tests
- Passed: X
- Skipped: Y
- Failed: Z

### ML Service Tests
- Passed: X
- Skipped: Y
- Failed: Z

### Issues Found
[List any failures or unexpected behavior]

### Recommendations
[Any suggested fixes or improvements]
