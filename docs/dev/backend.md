# Backend

The backend is a **FastAPI** application written in Python using `uv`.

## Package Layout

```
services/backend/src/
├── swen/
│   ├── application/    ← command/query handlers, orchestrating services, ports
│   ├── domain/         ← entities, value objects, domain services, ports
│   ├── infrastructure/ ← SQLAlchemy repos, FinTS adapter, ML client, SMTP
│   └── presentation/
│       ├── api/        ← FastAPI app factory, routers, schemas
│       └── cli/        ← CLI entry points (db-init, seed-demo, secrets)
├── swen_identity/      ← user management, auth, JWT
├── swen_config/        ← pydantic-settings config loader (immutable by user)
└── swen_demo/          ← demo data generation
```

## App Factory

The FastAPI application is created via `create_app()` in `swen/presentation/api/app.py`. It:

1. Loads settings from `swen_config`
2. Registers all routers (`/api/v1/...`)
3. Attaches the lifespan context manager and caches singletons (db engine, encryption keys, ml client)
4. Configures CORS, cookie settings, and exception handlers

## Dependency Injection

SWEN uses FastAPI's native `Depends()` for dependency injection. The `dependencies.py` module defines all shared dependencies:

| Dependency | Type Alias | Purpose |
|---|---|---|
| `get_db_session` | `DBSession` | Async database session (per-request) |
| `get_current_user` | `AuthenticatedUser` | Authenticated `User` from JWT bearer token |
| `get_current_current_user` | `CurrentUserContext` | `CurrentUser` context for repository scoping |
| `get_repository_factory` | `RepoFactory` | `SQLAlchemyRepositoryFactory` (auto-scoped to user) |
| `get_ml_client` | `MLClient` | `MLServiceClient` instance |
| `get_ml_port` | `MLPort` | `MLServicePort` for application layer |

Routers receive the repository factory via `factory: RepoFactory` and pass it to application layer classes through their `.from_factory()` classmethod. For example, from `services/backend/src/swen/presentation/api/accounting/routers/accounts.py`:

```python
@router.get("/accounts")
async def list_accounts(
    factory: RepoFactory,
    account_type: AccountTypeFilter = None,
) -> AccountListResponse:
    query = ListAccountsQuery.from_factory(factory)
    result = await query.execute(
        account_type=account_type,
        ...
    )
```

Application commands and queries implement `from_factory(factory: RepositoryFactory)` so they construct their own dependencies (repos, services) from the factory, keeping routers thin and explicit.

## Settings

Settings are loaded by `swen_config` using `pydantic-settings`. The loader discovers the env file by checking:

1. `APP_ENV` environment variable (`development` → `config/.env.dev`, otherwise `config/.env`)
2. The `config/` directory mounted at `/app/config` in Docker

Key settings groups:

| Group | Examples |
|---|---|
| Database | `POSTGRES_HOST`, `POSTGRES_PASSWORD`, `POSTGRES_DB` |
| Security | `ENCRYPTION_KEY`, `JWT_SECRET_KEY`, `API_COOKIE_SECURE` |
| CORS | `API_CORS_ORIGINS` |
| SMTP | `SMTP_HOST`, `SMTP_PORT`, `SMTP_ENABLED` |
| Registration | `REGISTRATION_MODE` (`open` / `admin_only`) |
| ML | `SWEN_ML_SERVICE_URL` |

## JWT Authentication

SWEN uses a **dual-token** JWT strategy:

| Token | Lifetime | Storage | Purpose |
|---|---|---|---|
| Access token | 24 hours | In-memory (JavaScript) | API authentication |
| Refresh token | 30 days | HttpOnly cookie | Silent token refresh |

The access token is passed as a `Bearer` header. The refresh token is set as a `Set-Cookie: refresh_token=...; HttpOnly; SameSite=Strict` response on login and used by the `/auth/refresh` endpoint to issue a new access token without re-entering credentials.

`API_COOKIE_SECURE=true` must be set in production (HTTPS only).

## Encryption at Rest

FinTS credentials (username + PIN) are encrypted with **Fernet** (AES-128-CBC + HMAC-SHA256) before being stored in the database. The `ENCRYPTION_KEY` in `config/.env` is the Fernet key. Never commit this key.

## Key Application Services

| Service | Location | Responsibility |
|---|---|---|
| `SyncBankAccountsCommand` | `application/integration/commands/` | Orchestrates multi-account batch sync |
| `BankAccountSyncService` | `application/integration/services/` | Per-IBAN sync: fetch → dedup → classify → import |
| `CounterAccountBatchService` | `application/integration/services/` | Batch ML classification + validation + fallback |
| `TransactionImportService` | `application/integration/services/` | Receives pre-resolved accounts, handles idempotency & persistence |
| `SyncNotificationService` | `application/integration/services/` | Stateful SSE event emitter for sync progress |
| `TransferReconciliationService` | `domain/integration/services/` | Internal transfer detection & reconciliation |
| `OpeningBalanceService` | `domain/accounting/services/opening_balance/` | First-sync opening balance creation |
| `BankAccountImportService` | `domain/integration/services/` | Creates and validates BankAccount ↔ Account links |

## CLI Entry Points

Defined in `pyproject.toml` `[project.scripts]`:

| Command | What it does |
|---|---|
| `swen setup` | Interactive guided setup wizard (generates secrets, writes `.env` for Docker or `.env.dev` for bare metal based on environment selection, runs db-init) |
| `swen secrets generate` | Prints three freshly-generated secrets (Fernet key, JWT key, DB password) |
| `db-init` | Creates all database tables (idempotent) |
| `db-drop` | Drops all database tables (destructive — no reset, just drop) |
| `db-reset` | Drops and recreates all tables (destructive) |
| `seed-demo` | Creates a demo user + sample accounts + ~200 transactions |
