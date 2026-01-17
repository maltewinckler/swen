# Backend Test Suite

## Overview

The test suite is organized by domain and test type:

```
tests/
├── swen/                    # Main accounting domain
│   ├── unit/               # Fast, isolated unit tests
│   └── integration/        # Database integration tests
├── swen_identity/          # Identity/auth domain
│   ├── unit/
│   └── integration/
├── cross_domain/           # Tests spanning multiple domains
│   └── integration/
├── external/               # Real bank connection tests
└── shared/fixtures/        # Shared test utilities
```

## Running Tests

### Unit Tests (no dependencies)

```bash
poetry run pytest tests/swen/unit/ tests/swen_identity/unit/ -v
```

### Integration Tests (requires Docker/Podman)

Integration tests use **Testcontainers** to spin up ephemeral PostgreSQL instances.

```bash
poetry run pytest tests/swen/integration/ -v
```

## Docker/Podman Setup

If you have Docker installed and running, Testcontainers should work out of the box. For the Podman, you need to have the podman.socket service running and the following env variables exported
    ```bash
    export DOCKER_HOST=unix:///run/user/$(id -u)/podman/podman.sock
    export TESTCONTAINERS_RYUK_DISABLED=true
    ```

## Test Markers

- `@pytest.mark.integration` - Requires database (auto-skipped without Docker)
- `@pytest.mark.external` - Connects to real banks (run with `--run-external`)
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.manual` - Requires manual TAN input

## External Bank Tests

Tests in `tests/external/` connect to real FinTS banks and require credentials:

```bash
# Set credentials in .env or environment
export FINTS_BLZ=...
export FINTS_USERNAME=...
export FINTS_PIN=...
export FINTS_ENDPOINT=...

# Run external tests
poetry run pytest tests/external/ --run-external -v
```
