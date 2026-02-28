# Backend

The backend is a **FastAPI** application written in Python 3.13, structured as a uv workspace member (`swen-backend`).

## Package Layout

```
services/backend/src/
├── swen/               ← main application package
│   ├── application/    ← use cases, command/query handlers
│   ├── domain/         ← entities, value objects, domain services, ports
│   ├── infrastructure/ ← SQLAlchemy repos, FinTS adapter, ML client, SMTP
│   └── presentation/
│       ├── api/        ← FastAPI app factory, routers, schemas
│       └── cli/        ← CLI entry points (db-init, seed-demo, secrets)
├── swen_identity/      ← user management, auth, JWT
├── swen_config/        ← pydantic-settings config loader
└── swen_demo/          ← demo data seeder
```

## App Factory

The FastAPI application is created via `create_app()` in `swen/presentation/api/app.py`. It:

1. Loads settings from `swen_config`
2. Registers all routers (`/api/v1/...`)
3. Attaches the lifespan context manager (DB connection pool init/teardown)
4. Configures CORS, cookie settings, and exception handlers

## Dependency Injection

SWEN uses FastAPI's native `Depends()` for dependency injection:

```python
@router.get("/transactions/{id}")
async def get_transaction(
    id: UUID,
    ctx: UserContext = Depends(get_current_user),
    repo: TransactionRepository = Depends(get_transaction_repo),
) -> TransactionDTO:
    ...
```

Repository implementations are injected via `Depends` — this makes them easy to swap in tests (pass a mock repo instead of the SQLAlchemy one).

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

## Authentication — JWT

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

| Service | Responsibility |
|---|---|
| `TransactionImportService` | Orchestrates a full bank sync: FinTS fetch → dedup → ML classify → Draft creation |
| `MLBatchClassificationService` | Re-classifies all unclassified Draft transactions in bulk |
| `AccountMappingService` | Creates and validates the link between a BankAccount and its bookkeeping Account |

## CLI Entry Points

Defined in `pyproject.toml` `[project.scripts]`:

| Command | What it does |
|---|---|
| `swen secrets generate` | Prints three freshly-generated secrets (Fernet key, JWT key, DB password) |
| `db-init` | Creates all database tables (idempotent) |
| `db-reset` | Drops and recreates all tables (destructive) |
| `seed-demo` | Creates a demo user + sample accounts + ~200 transactions |
