# Testing

SWEN has a layered test suite following the **test pyramid**: many fast unit tests, fewer slower integration tests, and a small number of external/manual tests.

## Test Pyramid

```
          ┌──────────┐
          │ External │  ~5 tests — real bank connections (never in CI)
          ├──────────┤
          │  Integr. │  ~25% — Testcontainers, ephemeral PostgreSQL
          ├──────────────────────────┤
          │         Unit             │  ~70% — pure Python, all I/O mocked
          └──────────────────────────┘
```

## Directory Structure

```
services/backend/tests/
├── swen/                    ← Main accounting domain
│   ├── unit/                ← Fast, isolated (no I/O)
│   └── integration/         ← Requires Postgres (Testcontainers)
├── swen_identity/           ← Identity/auth domain
│   ├── unit/
│   └── integration/
├── cross_domain/            ← Tests spanning multiple domains
│   └── integration/
├── external/                ← Real bank connections (manual only)
└── shared/fixtures/         ← Shared fixtures and utilities
```

## Running Tests

=== "All tests (unit + integration)"

    ```bash
    make test
    # or
    uv run pytest services/backend/tests/ -v -m "not external and not manual"
    ```

=== "Unit tests only (fast)"

    ```bash
    uv run pytest services/backend/tests/ -v -m "not integration and not external"
    ```

=== "Integration tests only"

    ```bash
    uv run pytest services/backend/tests/ -v -m integration
    ```

=== "With coverage"

    ```bash
    make test-cov
    ```

## Test Markers

| Marker | Meaning | Runs in CI |
|---|---|---|
| `@pytest.mark.integration` | Requires Postgres (Testcontainers) | ✅ Yes |
| `@pytest.mark.external` | Connects to a real bank | ❌ Never |
| `@pytest.mark.slow` | Long-running test | ✅ Yes |
| `@pytest.mark.manual` | Requires manual TAN input | ❌ Never |

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

## External Tests

Tests in `tests/external/` connect to real FinTS banks. They require valid bank credentials:

```bash
export FINTS_BLZ=...
export FINTS_USERNAME=...
export FINTS_PIN=...

uv run pytest tests/external/ -v --run-external
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

```bash
make test-ml
# or
uv run pytest services/ml/tests/ -v
```

ML tests live in `services/ml/tests/` and follow the same pyramid / marker conventions.
