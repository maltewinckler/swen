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
- **`execute(...)` inputs**: up to 4 scalar params directly in the signature. Beyond that, bundle them into an input DTO instead of growing the param list further (as `UpdateUserSettingsCommand` now does with `PreferencesUpdateDTO`). `update_account_command`/`create_account_command`/`list_transactions_query`/`create_external_account_command`/`export_report_query` (5–6 params) are pre-existing exceptions — don't add new ones.
- **`execute(...)` output**: always a DTO (see naming rule below), never a domain entity or a bare `dict`. The only exception is a genuine primitive (`bool`, `int`, `None`). `GenerateDefaultAccountsCommand` returning a raw `dict` is a pre-existing exception, not a pattern to copy.

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
- **Repository-factory pattern**: All `commands` and `queries` in the `application/` layer must implement a `from_factory` classmethod such that we can instantiate it directly from the factory that is defined as a dependency in our FastAPI app.

  ```python
  @classmethod
  def from_factory(cls, factory: RepositoryFactory) -> "MyQuery":
      return cls(repo=factory.some_repository())
  ```

  (`application/system/queries/database_integrity_query.py` is the single current exception — it takes a port directly and has no `from_factory` yet.)

### Naming: `DTO` / `Response` / `Request` suffixes

- Every application-layer data holder returned by a command/query is a `*DTO` (e.g. `AccountSummaryDTO`) — no bare `*Result`/`*Details`/etc. Remaining pre-existing exceptions, all still plain `@dataclass`: `TransactionListResult` (`accounting/queries/list_transactions_query.py`), `DashboardSummary` (`analytics/queries/dashboard_summary_query.py`), `IntegrityCheckResult` (`system/queries/database_integrity_query.py`). Don't add new ones; rename and migrate them to `BaseModel` opportunistically when you touch them, not in a blanket pass. `TransactionImportResult` is already a `BaseModel` but keeps its `*Result` name — rename it when you next touch the import service.
- A presentation schema that mostly just re-exposes a DTO (per the inheritance pattern below) is named after that DTO with the suffix swapped for what the schema is used for: `AccountSummaryDTO` → `AccountSummaryResponse` (output) or `...Request` (input) — not an unrelated name like `AccountResponse`.
- Every such schema should carry a `json_schema_extra` example. Response classes built via `.model_validate(dto)` additionally need `from_attributes=True` (see below) — plain `Request` schemas parsed from a JSON body normally don't.

### Presentation schemas: inherit from DTOs, don't duplicate fields

A `presentation/.../schemas/` response class should inherit directly from its application-layer DTO instead of hand-declaring the same fields a second time.

```python
# application/.../dtos/x_dto.py
class XDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: UUID
    amount: Decimal

# presentation/.../schemas/x.py
class XResponse(XDTO):
    """..."""
    model_config = ConfigDict(
        from_attributes=True,  # required if the DTO itself doesn't already set it
        json_schema_extra={"example": {...}},
    )
```

- **Prefer native types over primitive round-trips.** `UUID`, `Decimal`, and `datetime` are all first-class pydantic/FastAPI types — verified against this repo's pinned versions (pydantic 2.12, FastAPI 0.128): a `Decimal` field serializes over HTTP as an exact-precision JSON *string* (`"12.30"`, never a lossy float), `datetime` as ISO-8601, `UUID` as its string form — and all three get a *stricter* OpenAPI schema (`format: uuid` / `format: date-time` / a numeric `pattern`) than a hand-declared `str` field would. So DTOs should carry these types straight from the domain (`id: UUID`, `amount: Decimal`), not pre-convert to `str` "for JSON safety" — that conversion is unneeded, throws away schema precision, and forces the exact same cast back in every Response subclass (domain `UUID` → DTO `str` → Response `UUID` is pure waste). Two known holdouts that predate this rule and are *intentionally* deferred (not opportunistic): the CSV/`export_dto.py` DTOs (`TransactionExportDTO`/`AccountExportDTO`, `str`/`float` throughout — verify the exporter doesn't rely on the string form before changing), and `DiscoveredAccountDTO.balance`/`.balance_date` (`str` — crosses the discover→setup request contract, so it needs frontend coordination).
- Override a field only for a *real* divergence: a stricter validation constraint (`Literal[...]`, `pattern`), or genuinely different business content. If a DTO field's optionality or type looks wrong for what you're building (e.g. marked `Optional` only "to be safe" but never actually null), fix the DTO at the source instead of overriding it in every Response subclass. Leave a one-line comment saying why when you do override.
- If every field already matches the DTO, don't create a wrapper class at all: reference the DTO type directly, including as a nested field inside another response (`accounts: list[XDTO]`). Only keep a dedicated `XResponse` if it's also returned standalone from some endpoint.
- `model_config` merges up the inheritance chain — if the DTO already sets `from_attributes=True`, the subclass doesn't need to repeat it; if it doesn't, and the router builds the response via `.model_validate(dto)`, add `from_attributes=True` on the subclass.
- Once a response inherits from its DTO with matching native types, construct it in the router with `XResponse.model_validate(dto)`, not field-by-field kwargs — this cascades recursively through nested DTO/response pairs, and (once fields aren't secretly mismatched primitives) needs no special-casing.
- Schemas live next to their DTO's true domain owner, not necessarily next to the router that happens to consume them — e.g. `integration/routers/` legitimately imports schemas from both `accounting/schemas/` and `banking/schemas/`, since integration is the layer that bridges them (see §1). If a router imports schemas that live in one specific *other* single domain and nothing about the endpoint is cross-domain, that's a sign the router itself is filed in the wrong package — move the router, not the schema.
- **Don't force this pattern** when:
  - The DTO requires a field the request body doesn't have (e.g. `blz`/`iban` comes from the URL path, not the JSON body) — inheriting would leak the path param into the body schema.
  - The DTO is a plain `@dataclass`, not a Pydantic model — migrate it to `BaseModel` first (see "Migrating a dataclass DTO to Pydantic" below) rather than inheriting from a dataclass.
  - The DTO lacks validation constraints the request schema exists to enforce (`min_length`, `pattern`, etc.) — re-declaring every field to restore them defeats the point; a request schema with no boilerplate savings should just stay a plain `BaseModel`.

### Migrating a dataclass DTO to Pydantic

The accounting/analytics/events DTOs have all been migrated. Use this when converting one of the
remaining `@dataclass` holdouts listed above.

| Dataclass | Pydantic |
|---|---|
| `@dataclass(frozen=True)` | `class X(BaseModel):` + `model_config = ConfigDict(frozen=True)` |
| `field(default_factory=list)` | `field_name: list[T] = []` — Pydantic deep-copies defaults, so this is safe (verified: two instances do **not** share the list) |
| `dataclasses.asdict(self)` / `self.to_dict()` | `self.model_dump()` |
| a hand-rolled `_to_jsonable(...)` helper | `self.model_dump(mode="json")` |

- **Migrate the parent first** when a class inherits from another dataclass (the `SyncProgressEvent` event hierarchy was the common case).
- `from_entity` / `from_transaction` style factories stay `@classmethod` and work unchanged.
- Computed values: a bare `@property` stays out of `model_dump()`; add `@computed_field` above it when the value *should* be serialized.
- `model_dump()` returns native Python types; `model_dump(mode="json")` returns JSON-ready ones — `UUID` → `str`, `datetime` → ISO-8601 `str`, and `Decimal` → an **exact-precision `str`** (`"12.30"`), never a float. Use `mode="json"` for SSE payloads. (Verified against the pinned pydantic 2.12.)
- `frozen=True` is not optional — it preserves the immutability the dataclass had. Pydantic models are mutable by default.
- Keep `from __future__ import annotations`; forward refs in this codebase still need it.
- Beware `Field(..., init=False)`: on a `BaseModel` it is accepted but does **not** actually exclude the field from `__init__` (verified — the kwarg is still accepted). It only has that effect on pydantic dataclasses. Use it for the default value only, and don't rely on it for enforcement.

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
- `swen.presentation.api.dependencies.get_current_user` imports `swen_identity.domain` directly and instantiates `UserRepositorySQLAlchemy(session)` in-place (no ACL yet; the FastAPI dependency is where "get current user" lives — there is no `application/queries/user/` module).
- `swen.presentation.api.{auth/routers/auth, admin/routers/admin}` instantiate SQLAlchemy repos and call `session.commit()` directly; `settings/routers/preferences` also calls `factory.session.commit()` directly (4 sites). (The `integration/routers/sync` router is clean — do not re-add it here.)
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
npm run dev          # dev server
npm test             # vitest (add -- --run for a single non-watch pass)
npm run lint         # eslint
npx tsc --noEmit     # typecheck (there is no `typecheck` script)
npm run build        # vite production build
```

Stack:
```bash
docker compose up -d            # postgres + ml + searxng
make help                       # see project shortcuts
```

---

*Last updated: 2026-07-24. Update this file when you change a convention — don't let it rot.*
