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
- **Domain depends on nothing else** in the project, with one exception: `swen_config` (Pydantic `Settings`) is allowed everywhere, including `domain/`. It's a dependency-free leaf package — it imports nothing from `swen`/`swen_identity`, so injecting `Settings` doesn't create a real layering violation, just a plain config value. No SQLAlchemy, no FastAPI, no third party packages that are not explicitly allowed, no other infra imports.
- **Application depends only on `domain`, its own `application/ports/`, and `swen_config`**. It must NOT import from `infrastructure` or `presentation`. Two exceptions: the FinTS concerns (which is strictly speaking infrastructure) in the `RepositoryFactory` in `application/factories/repository_factory.py`, and `swen_config.Settings` where a use case genuinely needs a config value (e.g. `forgot_password_command.py`/`reset_password_command.py` need `frontend_base_url` to build a reset link). This simplifies our code significantly.
- **Infrastructure implements interfaces declared in `domain/.../repositories/` or `application/ports/`**.
- **Presentation wires things up** (dependencies.py / FastAPI `Depends`) and translates HTTP and application DTOs.
- **Cross-bounded-context** (`swen` and `swen_identity`): only via well-defined ports/DTOs in `application/ports/identity` and `application/context/`. Don't reach into the other context's domain/infra directly.
- Repository interfaces live in **`domain/<aggregate>/repositories/`**. SQLAlchemy implementations live in **`infrastructure/persistence/sqlalchemy/repositories/`** with the suffix `*SQLAlchemy`.

### MUST NOT (real anti-patterns already present, don't add more)
- ❌ `from swen.application.factories import RepositoryFactory` inside `domain/`. Domain must not know about application.
- ❌ `from swen.infrastructure...` inside `application/` (commands, services, factories). Define a Protocol port instead.
- ❌ Direct repository instantiation (`UserRepositorySQLAlchemy(session)`) inside routers. Always go through the factory.
- ❌ `await factory.session.commit()` inside a router. Commits belong to the application layer / Unit of Work.
- ❌ `self._session.commit()` / `self._session.rollback()` anywhere inside a repository method. See "Unit of Work / transaction boundaries" below — repositories persist, only the `UnitOfWork` commits or rolls back.
- ❌ `from swen_identity.domain...` in `swen.application` (anti-corruption layer pending). New code: depend on `swen.application.ports.identity` only.
- ❌ Putting ML/classification fields directly on the `Transaction` aggregate — model them as a separate value object/aggregate.

### Aggregates / Entities
- Aggregates expose **methods** that enforce invariants. No public mutable attributes. No setter-only "anemic" entities.
- Value objects are **frozen** Pydantic models: `model_config = ConfigDict(frozen=True, validate_assignment=True)`. Prefer declarative constraints (`Field(ge=1)`) over hand-rolled `__post_init__` validation.
- **Value object vs. service-local carrier** — not every small frozen class is a value object, and the distinction decides where it lives:
  - A **value object / aggregate** is a shared domain concept with meaning beyond one call site (`Money`, `Currency`, `SyncPeriod`). It lives in `domain/<domain>/value_objects/`, is exported from that package's `__init__`, and **must** be a frozen Pydantic model.
  - A **service-local carrier** just ferries one service's output to its caller. It may hold domain objects, is never serialized, and is produced/consumed inside a single layer. Declare it **in the same module as its service**, export it from **no** `__init__`, and leave it a plain frozen `dataclass`. See `ExternalAccountResult` (`domain/integration/services/external_account_management_service.py`) and `TransactionImportOutcome` (`application/integration/services/transaction_import_service.py`).
  - Putting a carrier in `value_objects/` is a real error, not a style nit: it advertises a shared concept that doesn't exist and pollutes the domain's public surface. When unsure, ask "would a second, unrelated call site want this type?" — if no, it's a carrier.
- Time: use `swen.domain.shared.time.utc_now()` inside `swen`. **Do not** import it from `swen_identity` (and vice versa) — duplicate it per context to keep BCs decoupled.

### Application layer
- One **Command** (write) or **Query** (read) per use case. Keep them small.
- Commands are constructed via DI in routers and call `await command.execute(...)`.
- **Commands/Queries are leaf use-case handlers, reached only from `presentation/` routers** (or an equivalent entry point — e.g. a scheduled job — if one is ever added), and each router endpoint calls at most one. A Command/Query must never construct or call another Command/Query's `execute()`. `CreateSimpleTransactionCommand` wrapping `CreateTransactionCommand.execute()` (`application/accounting/commands/create_simple_transaction_command.py`) is a pre-existing exception, not a pattern to copy — if two commands need the same logic, pull it into a domain service both call directly instead of nesting commands. Composing several **domain services** inside one command/service is fine and is the intended shape (`BankAccountSyncService` composing `OpeningBalanceService` + `BankFetchService` + `BankBalanceService` is the example to follow).
- Validation: structural in Pydantic schemas (presentation), invariants in domain, business rules in commands. Don't `try/except ValueError` over raw Enum casts in routers — raise typed domain errors.
- Long orchestrators (>~300 LOC) are a smell — split into focused services. The current `transaction_import_service.py` is the example *not* to follow further.
- **`execute(...)` inputs**: up to 4 scalar params directly in the signature. Beyond that, bundle them into an input DTO instead of growing the param list further (as `UpdateUserSettingsCommand` now does with `PreferencesUpdateDTO`). `update_account_command`/`create_account_command`/`list_transactions_query`/`create_external_account_command`/`export_report_query` (5–6 params) are pre-existing exceptions — don't add new ones.
- **`execute(...)` output**: always a DTO (see naming rule below), never a domain entity or a bare `dict`. The only exception is a genuine primitive (`bool`, `int`, `None`). `GenerateDefaultAccountsCommand` returning a raw `dict` is a pre-existing exception, not a pattern to copy.

### Unit of Work / transaction boundaries
A **logical operation is one `execute()` call, and one `execute()` call has exactly one commit.** The transaction boundary belongs to the command/service that owns the use case, never to the repository underneath it.

- **Repositories never call `self._session.commit()` or `.rollback()`.** A repository method may `add()`/`flush()`/`execute()` statements, but the session's fate (commit vs. rollback) is not its decision — it doesn't know whether it's the only write in the operation. `find_*`/read methods obviously never commit either.
- **Commands/services acquire a `UnitOfWork` from the factory and wrap the whole use case in it**, the same shape as `StoreCredentialsCommand`/`UpdateCredentialsCommand` (`application/banking/commands/credentials/`):

  ```python
  class SomeCommand:
      def __init__(self, some_repository: SomeRepository, uow: UnitOfWork):
          self._repo = some_repository
          self._uow = uow

      @classmethod
      def from_factory(cls, factory: RepositoryFactory) -> SomeCommand:
          return cls(
              some_repository=factory.some_repository(),
              uow=factory.unit_of_work(),
          )

      async def execute(self, ...) -> SomeDTO:
          async with self._uow:
              # every read/write for this use case happens in here,
              # across as many repositories as needed.
              ...
  ```

  `UnitOfWork.__aexit__` commits on clean exit and rolls back on exception (`application/ports/unit_of_work.py`, `infrastructure/persistence/sqlalchemy/unit_of_work.py`) — that is the **only** place a commit happens.
- **If a use case touches several repositories, that's still one `uow` block**, not one commit per repository call. Don't reach for a "helper that commits for me" inside a repository as a shortcut — inject the repositories the command/service needs and do it all inside its own `async with self._uow:`.
- **A command that composes several domain services/repositories for one use case is still one `uow` block** (e.g. a sync service that fetches, stores transactions, updates credential metadata, and processes an import batch — see `BankAccountSyncService.sync_account()`). If you can't tell from reading the command alone "did this fully succeed or partially?", the boundary is wrong — trace-into-each-repo-to-find-the-commit is the failure mode this rule exists to prevent. This never means reaching for another Command to do part of the work (see Application layer above) — compose domain services instead.
- **When a command loops over independent units of work**, each iteration gets its own `uow`, not one shared across the whole loop. `SyncBankAccountsCommand` iterating account mappings and catching/logging per-mapping failures so one account's failure doesn't undo another's already-committed sync is the example — the `uow` boundary belongs inside `sync_account()` (one per mapping), not wrapped around the `for mapping in mappings:` loop.
- **Sub-atomic grouping inside one `uow`** (e.g. two writes across two repositories that must land together, but are part of a bigger operation) uses savepoint-if-nested / begin-if-top-level, but **never commits itself** — it only groups; the enclosing `UnitOfWork` still owns the commit. `TransactionImportRepositorySQLAlchemy._atomic_scope()` (used by `save_complete_import`/`mark_reconciled_as_internal_transfer`) is the reference example: `begin_nested()` when already inside a transaction, `begin()` otherwise, no trailing commit either way.
- **Repositories translate `IntegrityError` from driver-native structure, never from rendered message text.** SQLAlchemy's asyncpg dialect wraps the raw driver exception before exposing it as `exc.orig`, so check `exc.orig.sqlstate` (SQL-standard, e.g. `"23505"` for unique_violation) or SQLite's `exc.orig.sqlite_errorcode`, not `str(exc)`/`str(exc.orig)` — driver wording drifts across versions/locales, SQLSTATE codes don't. Only translate the specific violation you've confirmed and recognize; re-raise anything else so it isn't laundered into a misleading exception type. See `AccountRepositorySQLAlchemy` (`_is_unique_violation`/`_unique_constraint_name`) for the pattern, including reading `exc.orig.__cause__.constraint_name` where the dialect chains the original driver exception.
- New repository methods: if you're about to write `await self._session.commit()`, stop — add a `uow: UnitOfWork` parameter to the calling command/service instead.

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

- Every application-layer data holder returned by a command/query is a `*DTO` (e.g. `AccountSummaryDTO`) — no bare `*Result`/`*Details`/etc. There are **no remaining exceptions**; keep it that way. A query must never hand domain entities to presentation, directly or nested inside its result — map to DTOs inside `execute()` so the router is just `XResponse.model_validate(dto)`. `ListTransactionsQuery` and `DashboardSummaryQuery` are the worked examples.
- **Not everything in `application/` is a DTO.** Results passed *between* application services that never reach presentation, and that legitimately carry domain objects, are **not** DTOs — don't give them a `*DTO` suffix and don't move them into `dtos/`. Name them `*Outcome` and declare them next to the service that produces them. The reference example is `TransactionImportOutcome` (`integration/services/transaction_import_service.py`): it holds `BankTransaction`/`Transaction` behind `arbitrary_types_allowed=True`, flows import → sync, and is consumed only by `compute_stats`. Slapping `*DTO` on such a type is worse than leaving it unsuffixed — it invites someone to serialize it or return it from an endpoint, which is exactly the domain-entity leak the DTO rule exists to prevent. (Corollary of the `application/dtos/` location rule in §3: if it doesn't live there, it probably isn't a DTO.)
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
8. **Password hashing**: bcrypt via the existing `BcryptPasswordHashingAdapter` (implements `swen_identity.domain.ports.PasswordHashingPort`) — do not introduce another hasher. Validation today is length-only; if you change it, update tests.
9. **Rate limiting / token revocation are not yet implemented.** Don't claim they are; if you add an endpoint that needs them, flag it.

## 6. Known Debt (don't accidentally "fix" by deleting)

These are tracked weak spots; if you touch them, fix don't paper over.

- `swen.domain.accounting.services.account_hierarchy_service` imports `application.factories` (layer violation).
- `swen.application.commands.integration.transaction_sync_command` imports infrastructure dispatcher / ML client directly.
- `swen.application.factories.repository_factory` imports concrete `FinTSConfigRepository` / `GeldstromApiConfigRepository` from `swen.infrastructure` — should be ports.
- `swen_identity.domain.aggregates.user` imports `swen.domain.shared.time.utc_now` (cross-BC).
- `swen.presentation.api.dependencies.get_current_user` imports `swen_identity.domain` directly and instantiates `UserRepositorySQLAlchemy(session)` in-place (no ACL yet; the FastAPI dependency is where "get current user" lives — there is no `application/queries/user/` module). Note the ACL *does* now run one level up, in `get_repository_factory` (`IdentityAdapter.to_current_user(UserContext.create(user))`) — this bullet is about `get_current_user` itself, which still returns a raw `swen_identity.User`.
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
