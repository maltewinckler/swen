# AGENTS.md

Guidance for AI coding agents (and humans) working in the **swen** repository.
This file documents the conventions actually used in the codebase and the rules to follow when adding or changing code.

> If you find yourself fighting the patterns below, stop and ask. Do not introduce a new one.

## 1. Repository Layout

```
services/
  backend/      # FastAPI + SQLAlchemy (async) — Python 3.x, DDD layered
    src/
      swen/                # Main bounded context (accounting, banking, integration)
        domain/            # Pure domain: entities, aggregates, VOs, repo interfaces, domain services
        application/       # Use cases: commands, queries, DTOs, ports, factories
        infrastructure/    # Adapters: SQLAlchemy repos, FinTS, ML client, email, ...
        presentation/      # FastAPI routers, schemas, exception handlers, dependencies
      swen_identity/       # Bounded context: users, auth, JWT, password reset
        (same domain/application/infrastructure/presentation split)
      swen_config/         # Pydantic Settings (env-driven configuration)
      swen_demo/           # Seed/demo data
    tests/
      swen/                # mirrored unit/integration per layer
      swen_identity/
      cross_domain/        # security & multi-tenant isolation tests
      external/            # tests touching real third parties (FinTS) — `manual`
      shared/              # test helpers, fixtures
  contracts/    # `swen_ml_contracts` Pydantic schemas shared between backend and ml service
  ml/           # `swen_ml` FastAPI service: embeddings, classification, training
  frontend/     # Vite + React 18 + TS, TanStack Router, React Query, Tailwind, Vitest
  database/     # init SQL
  searxng/      # search engine config
docs/           # MkDocs (`zensical.toml` is the site config)
config/         # Environment files (.env.* — never commit real secrets)
```

The backend is a **monolith with internal bounded contexts** (`swen`, `swen_identity`). Treat them as if they could be split into separate services.
Moreover, make sure that the domains in `swen` stay clean: Do not leak `banking` concerns into `accounting` concerns and use the `integration` layer
for integration between banking and accounting.

## 2. Architectural Rules (DDD)

The dependency direction is strictly:

```
presentation ──► application ──► domain
       │                ▲
       └──► infrastructure (implements domain ports)
```

### MUST
- **Domain depends on nothing else** in the project. No SQLAlchemy, no FastAPI, no infra imports.
- **Application depends only on `domain` and on its own `application/ports/`**. It must NOT import from `infrastructure` or `presentation`. The only exception is the FinTS concerns (which is strictly speaking infrastructure) in the `RepositoryFactory` in `application/factories/repository_factory.py`. This simplifies our code significantly.
- **Infrastructure implements interfaces declared in `domain/.../repositories/` or `application/ports/`**.
- **Presentation wires things up** (dependencies.py / FastAPI `Depends`) and translates HTTP and application DTOs.
- **Cross-bounded-context** (`swen` and `swen_identity`): only via well-defined ports/DTOs in `application/ports/identity` and `application/context/`. Don't reach into the other context's domain/infra directly.
- Repository interfaces live in **`domain/<aggregate>/repositories/`**. SQLAlchemy implementations live in **`infrastructure/persistence/sqlalchemy/repositories/`** with the suffix `*SQLAlchemy`.

### MUST NOT (real anti-patterns already present, don't add more)
- ❌ `from swen.application.factories import RepositoryFactory` inside `domain/`. Domain must not know about application.
- ❌ `from swen.infrastructure...` inside `application/` (commands, services, factories). Define a Protocol port instead.
- ❌ Direct repository instantiation (`UserRepositorySQLAlchemy(session)`) inside routers. Always go through the factory.
- ❌ `await factory.session.commit()` inside a router. Commits belong to the application layer / Unit of Work.
- ❌ `from swen_identity.domain...` in `swen.application` (anti-corruption layer pending). New code: depend on `swen.application.ports.identity` only.
- ❌ Putting ML/classification fields directly on the `Transaction` aggregate — model them as a separate value object/aggregate.

### Aggregates / Entities
- Aggregates expose **methods** that enforce invariants. No public mutable attributes. No setter-only "anemic" entities.
- Value objects are **frozen** Pydantic models: `model_config = ConfigDict(frozen=True, validate_assignment=True)`.
- Time: use `swen.domain.shared.time.utc_now()` inside `swen`. **Do not** import it from `swen_identity` (and vice versa) — duplicate it per context to keep BCs decoupled.

### Application layer
- One **Command** (write) or **Query** (read) per use case. Keep them small.
- Commands are constructed via DI in routers and call `await command.execute(...)`.
- Validation: structural in Pydantic schemas (presentation), invariants in domain, business rules in commands. Don't `try/except ValueError` over raw Enum casts in routers — raise typed domain errors.
- Long orchestrators (>~300 LOC) are a smell — split into focused services. The current `transaction_import_service.py` is the example *not* to follow further.

### Repository pattern (multi-tenant)
Every repository is constructed by `RepositoryFactory` and is **automatically scoped to `current_user.user_id`**. This is the project's main auth boundary.

```python
class XRepositorySQLAlchemy:
    def __init__(self, session: AsyncSession, current_user: CurrentUser):
        self._user_id = current_user.user_id
```

When adding a repository:
1. Define the interface in `domain/<aggregate>/repositories/`.
2. Implement it in `infrastructure/persistence/sqlalchemy/repositories/`.
3. Add a method to `RepositoryFactory` (Protocol) **and** the SQLAlchemy factory.
4. **Every** query MUST filter by `self._user_id` unless the table is global (and that needs review).

## 3. Backend Conventions

- **Python**: type hints everywhere; `from __future__ import annotations` at top of modules with forward refs.
- **Async**: SQLAlchemy 2.x async; `await` everything I/O.
- **Config**: `swen_config.settings.Settings` (Pydantic Settings). Never read `os.getenv` directly in domain/application code. Inject `Settings`.
- **DTOs**: live in `application/dtos/`. Never serialize domain entities to API responses directly — map to a presentation schema.
- **Errors**: raise domain exceptions; map them once in `presentation/api/exception_handlers.py`. New endpoint? Don't reinvent error mapping — register your exception type there.
- **Logging**: `logger = logging.getLogger(__name__)`. Use `logger.exception(...)` in `except` blocks. Do not log secrets, PINs, full tokens, or full request bodies.
- **Crypto**: use `cryptography.fernet` via the existing `ENCRYPTION_KEY` setting for stored bank credentials. Never roll your own. For randomness in security-sensitive paths use `secrets`, not `random`.
- **JWT**: `HS256`, hardcoded algorithm list — keep it that way (alg confusion mitigation).
- **SQL**: parameterized only. `text(":param")` + `params={}` is fine. f-strings into `text(...)` are forbidden.
- **Repository-factory pattern**: All `commands` and `queries` in the `application/` layer must implement a `from_repo_factory` classmethod such that we can instantiate it directly from the factory that is defined as a dependency in our FastAPI app.

### Tests
- Layout mirrors source: `tests/swen/unit/<layer>/...`, `tests/swen/integration/...`.
- Markers: `unit`, `integration`, `manual` (for tests requiring real banking creds — never run in CI).
- Use the workspace tasks: **Run Unit Tests**, **Run Integration Tests**, **Run All Tests**.
- Integration tests need: `RUN_INTEGRATION=1 ENCRYPTION_KEY=… JWT_SECRET_KEY=… POSTGRES_PASSWORD=…`.
- Cross-context tenant isolation tests live in `tests/cross_domain/integration/security/` — extend them whenever you add a user-scoped resource.
- Agent-testing: We have a test agent prompt defined in `.github/prompts/verify-swen-end-to-end.prompt.md`. When we have added new functionality to swen, we should update this prompt to also verify the production-functionality of it.

## 4. Frontend Conventions (`services/frontend`)

- **Stack**: Vite + React 18 + TS strict + TanStack Router + React Query + Zustand + Tailwind + Vitest.
- **Routing**: file-based under `src/routes/`. Auth-gated pages live under `src/routes/_app/`. Don't edit `routeTree.gen.ts`.
- **API**: HTTP client in `src/api/client.ts`; per-resource modules in `src/api/`. Don't duplicate logic in `src/services/` — extend the existing module.
- **State**:
  - Server state: React Query (`useQuery` / `useMutation` + `queryClient.invalidateQueries`).
  - Client/UI state: Zustand stores in `src/stores/`.
- **Forms**: validate inline on change (clear field error on input, see `AccountEditModal`). Don't only validate on submit. Always `aria-required`, `aria-invalid`, `aria-describedby` via the existing `FormField` component.
- **Modals**: use the shared `Modal` component. It manages focus, ESC, stacking. Destructive actions go through `ConfirmDialog`.
- **Toasts**: use the shared `toast` API (`toast.success/danger/...`). Don't add ad-hoc notification components.
- **Loading**: prefer the existing skeleton components (`WidgetLoadingState`, `WizardLoadingState`) over a bare spinner for any layout that would otherwise shift.
- **i18n**: locale and currency are currently hardcoded (`de-DE`, `EUR`) in `lib/utils.ts`. New user-visible strings should at minimum funnel through one place — don't sprinkle hardcoded German / English strings further. A real i18n layer is pending.
- **Accessibility**: every icon-only button needs `aria-label`. Async status regions need `aria-live="polite"`.
- **PWA**: `public/sw.js` is conservative — bump `CACHE_NAME` whenever you change cached assets.
- **Types**: no `any`, no `@ts-ignore`. The codebase is currently clean; keep it that way.

## 5. Security Rules (do not break)

1. **Never commit secrets.** `.env*` is gitignored. Keep it that way. If you ever paste real credentials into the chat / a file, rotate them. The repo has previously been used with real FinTS credentials; treat that area with extra care.
2. **All user-scoped queries filter by `current_user.user_id`** via the repository factory. If you write raw SQL or bypass the factory, that's a security review.
3. **Don't disable JWT algorithm pinning** (`algorithms=[ALGORITHM]`).
4. **Don't widen CORS** (`allow_origins=["*"]` + `allow_credentials=True` is forbidden by spec — and we rely on it).
5. **Don't log** PIN, password, full tokens, or `request.body` containing credentials. The FinTS path is especially sensitive.
6. **State-changing endpoints**: POST/PUT/DELETE only. SameSite cookie + bearer token is the CSRF strategy — don't add cookie-only state-changing GETs.
7. **External URLs from settings** (e.g. `ML_SERVICE_URL`) should not become user-controllable inputs. Treat them as trusted only at startup.
8. **Password hashing**: bcrypt via the existing `PasswordService` — do not introduce another hasher. Validation today is length-only; if you change it, update tests.
9. **Rate limiting / token revocation are not yet implemented.** Don't claim they are; if you add an endpoint that needs them, flag it.

## 6. Known Debt (don't accidentally "fix" by deleting)

These are tracked weak spots; if you touch them, fix don't paper over.

- `swen.domain.accounting.services.account_hierarchy_service` imports `application.factories` (layer violation).
- `swen.application.commands.integration.transaction_sync_command` imports infrastructure dispatcher / ML client directly.
- `swen.application.factories.repository_factory` imports concrete `FinTSConfigRepository` / `GeldstromApiConfigRepository` from `swen.infrastructure` — should be ports.
- `swen_identity.domain.user.aggregates.user` imports `swen.domain.shared.time.utc_now` (cross-BC).
- `swen.application.queries.user.get_current_user_query` imports `swen_identity.domain` directly (no ACL yet).
- `swen.presentation.api.routers.{auth,admin,sync}` instantiate SQLAlchemy repos / call `session.commit()` directly.
- `Transaction` aggregate carries ML classification fields (`merchant`, `is_recurring`, `recurring_pattern`) that should be a separate VO.
- `ml_service_url` and similar external URLs lack validation.
- Encryption key rotation: `encryption_version` field exists, rotation logic does not.
- Frontend: `useSyncProgress` has a stale-closure risk over `options`; `AddTransactionModal` issues 4 separate account queries.

## 7. Doing Work

1. **Read before writing.** Open the relevant `domain/` and `application/` modules before adding to `infrastructure/` or `presentation/`.
2. **Mirror the layer.** New write → command + domain method + repo method. New read → query + DTO + read port.
3. **Run the right tests.** Use the workspace tasks. For backend changes, at minimum: unit + the touched integration suite.
4. **No unrelated refactors.** Findings in section 6 are intentional debt, not things to silently fix in an unrelated PR.
5. **Don't add docstrings, comments, or types to code you didn't change** unless the change requires it.
6. **Don't introduce new top-level dependencies** without a reason — both backend and frontend lock files are stable.
7. **Date / time**: use `utc_now()` from the bounded context you're in, never `datetime.utcnow()` (deprecated) or naive `datetime.now()`.

## 8. Quick Commands

Backend:
```bash
# Unit tests
.venv/bin/python -m pytest services/backend/tests -m "not integration and not manual" -q

# Integration tests (requires Postgres up via docker compose)
RUN_INTEGRATION=1 ENCRYPTION_KEY=… JWT_SECRET_KEY=… POSTGRES_PASSWORD=… \
  .venv/bin/python -m pytest services/backend/tests -m integration -q
```

Frontend:
```bash
cd services/frontend
npm dev          # dev server
npm test         # vitest
npm typecheck
npm lint
```

Stack:
```bash
docker compose up -d            # postgres + ml + searxng
make help                       # see project shortcuts
```

---

*Last updated: 2026-04-30. Update this file when you change a convention — don't let it rot.*
