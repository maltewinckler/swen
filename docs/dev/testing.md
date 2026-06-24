# Testing

SWEN has a layered test suite following the **test pyramid**: many fast unit tests, fewer slower integration tests, and a small number of external/manual tests.

## Test Pyramid

```
          ┌──────────┐
          │ External │  ~2 tests — real bank connections (never in CI)
          ├──────────┤
          │  Integr. │  ~25% — Testcontainers, ephemeral PostgreSQL
          ├──────────────────────────┤
          │         Unit             │  ~70% — pure Python, all I/O mocked
          └──────────────────────────┘
```

## Directory Structure

```
services/backend/tests/
├── swen/                    ← Main accounting/banking domain
│   ├── unit/                ← Fast, isolated (no I/O)
│   └── integration/         ← Requires Postgres (Testcontainers)
├── swen_identity/           ← Identity/auth domain
│   ├── unit/
│   └── integration/
├── cross_domain/            ← Tests spanning multiple domains
│   ├── integration/         ← Tenant isolation, multi-context tests
│   └── e2e/                 ← Full user journeys (bank connection, cash transactions)
├── external/                ← Real bank connections (manual only)
│   ├── fints/
│   ├── gateway/
│   └── tan/
└── shared/                  ← Shared fixtures and utilities
```

## Running Tests

### Podman Users: Required Configuration

If you use **Podman** instead of Docker, you must set the `DOCKER_HOST` environment variable before running tests. The testcontainers library uses this to locate the Podman socket.

```bash
# Set this before running tests (add to your .bashrc or .zshrc for persistence)
export DOCKER_HOST="unix:///run/user/$(id -u)/podman/podman.sock"
```

Without this, you will see errors like:
```
docker.errors.DockerException: Error while fetching server API version:
('Connection aborted.', FileNotFoundError(2, 'No such file or directory'))
```

### Test Commands

=== "All tests (unit + integration)"

    ```bash
    make test-backend
    # or
    uv run pytest services/backend/tests/ -v
    ```

=== "Unit tests only (fast)"

    ```bash
    uv run pytest services/backend/tests/swen/unit/ services/backend/tests/swen_identity/unit/ -v
    ```

=== "Integration tests only"

    ```bash
    uv run pytest services/backend/tests/ -v --run-integration
    # or
    RUN_INTEGRATION=1 uv run pytest services/backend/tests/ -v -m integration
    ```

=== "With coverage"

    ```bash
    make test-cov
    ```

=== "ML service tests"

    ```bash
    make test-ml
    # or
    uv run pytest services/ml/tests/ -v
    ```

## Test Markers

| Marker | Meaning | Runs in CI |
|---|---|---|
| `@pytest.mark.integration` | Requires Postgres (Testcontainers) | ✅ Yes |
| `@pytest.mark.external` | Connects to a real bank | ❌ Never |
| `@pytest.mark.slow` | Long-running test (>1s) | ✅ Yes |
| `@pytest.mark.manual` | Requires manual intervention | ❌ Never |
| `@pytest.mark.tan` | Requires manual TAN input | ❌ Never |

## Unit Tests

Unit tests have **zero I/O** — no database, no HTTP, no file system. All external dependencies are mocked with `pytest-mock`.

```python
def test_transaction_must_balance():
    account = Account(...)
    with pytest.raises(DomainError, match="Transaction must balance"):
        Transaction.create(journal_entries=[...])  # unbalanced entries
```

## Integration Tests — Testcontainers

Integration tests spin up an **ephemeral PostgreSQL container** per test session using [Testcontainers](https://testcontainers.com/). The container is destroyed after the session — no cleanup required, no shared state between runs.

```python
@pytest.mark.integration
async def test_import_creates_bank_transactions(db_session):
    repo = BankTransactionRepository(db_session)
    # ... real DB calls against a fresh Postgres container
```

### Podman Users

If you use Podman instead of Docker:

```bash
export DOCKER_HOST=unix:///run/user/$(id -u)/podman/podman.sock
export TESTCONTAINERS_RYUK_DISABLED=true
```

### Test Secrets

Integration tests use **hardcoded test secrets** (not real credentials):

```yaml
RUN_INTEGRATION: "1"
ENCRYPTION_KEY: "X6gejiP08L9cH4nW4bQk8aGo961x2rhGE40jOg67VwU="
JWT_SECRET_KEY: "test-jwt-secret-for-ci"
POSTGRES_PASSWORD: "test-password-not-used"
```

### Running All Integration Tests

```bash
uv run pytest services/backend/tests/swen/integration/ \
  services/backend/tests/swen_identity/integration/ \
  services/backend/tests/cross_domain/integration/ \
  services/backend/tests/cross_domain/e2e/ -v
```

## External Tests

Tests in `tests/external/` connect to real FinTS banks. They require valid bank credentials:

```bash
export FINTS_BLZ=...
export FINTS_USERNAME=...
export FINTS_PIN=...

uv run pytest tests/external/ -v --run-manual --run-external
```

These tests are **never run in CI**. Run them manually before a release if you want to validate bank connectivity.

## CI Policy

| Test type | When runs |
|---|---|
| Unit | Every push, every PR |
| Integration | Every push, every PR |
| External | Never automatically |
| Manual | Never automatically |

See [CI / GitHub Actions](ci.md) for the full workflow breakdown.

## ML Tests

ML tests live in `services/ml/tests/` and follow the same unit/integration pyramid:

```
services/ml/tests/
├── unit/
└── integration/
```

```bash
make test-ml
# or
uv run --package swen-ml pytest services/ml/tests/ -v
```
