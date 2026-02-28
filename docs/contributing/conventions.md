# Code Conventions

## Python

### Formatter and Linter: Ruff

All Python code is formatted and linted with **Ruff** (replaces Black + isort + flake8):

```bash
make lint         # check only (exits non-zero on violations)
make format       # auto-fix formatting
```

Key settings (`pyproject.toml`):

| Setting | Value |
|---|---|
| Line length | 88 characters |
| Selected rules | `E`, `F`, `I`, `UP`, `B`, `SIM` |
| Python version | 3.13 |

### Type Hints

All new functions and methods should have type annotations. Use `pyright` in basic mode:

```bash
uv run pyright services/backend/src/
```

### Domain Language

Use the **[ubiquitous language](../concepts/domain-model.md)** in code. Specifically:

- Use `Transaction` (not `entry`, `record`, or `booking`) for double-entry records
- Use `BankTransaction` (not `raw_transaction` or `statement_line`) for bank data
- Use `Account` for bookkeeping accounts, `BankAccount` for IBAN accounts
- Use `post` (not `confirm`, `approve`, or `save`) for the action of finalising a Draft

### Architecture Rules

- **No business logic in presentation layer** — routers only call application layer use cases
- **No framework imports in domain** — domain entities must not import FastAPI, SQLAlchemy, etc.
- **Repository interfaces in domain** — concrete implementations live in infrastructure
- **Commands return nothing** (or just an ID); **Queries return DTOs**

---

## TypeScript / Frontend

### Linter: ESLint + TypeScript

```bash
cd services/frontend && npm run lint
cd services/frontend && npx tsc --noEmit
```

- Strict TypeScript (`"strict": true` in `tsconfig.app.json`)
- No `any` unless absolutely necessary (use `unknown` + type guards)
- Component files: PascalCase (`TransactionList.tsx`)
- Utility/hook files: camelCase (`useTransactions.ts`)

---

## Git

### Commit Messages

No enforced format, but the convention used in this repo is:

```
[Type] Short description (present tense, ≤ 72 chars)

Optional body explaining why (not what — the diff shows what).
```

Common types: `Fix`, `Add`, `Remove`, `Refactor`, `Docs`, `Chore`, `Test`

Examples:

```
Fix: prevent duplicate BankTransactions on partial-day re-import
Add: Tier 0 IBAN anchor to ML classification pipeline
Docs: add double-entry bookkeeping primer
```

### PR Titles

Use the format `[Type] Short description`:

```
[Fix] Correct sequence numbering for same-day duplicate transactions
[Feature] Add keyword pattern management UI
[Chore] Bump uv to 0.7
[Docs] Implement MkDocs documentation site
```

### Branching

| Branch | Purpose |
|---|---|
| `main` | Always deployable, CI must be green |
| `feature/short-name` | Feature development |
| `fix/short-name` | Bug fixes |
| `chore/short-name` | Dependency bumps, tooling |
| `docs/short-name` | Documentation only |

---

## Documentation

- Write in plain, clear English
- Use admonitions (`!!! note`, `!!! warning`, `!!! tip`) for callouts
- Use Mermaid for diagrams (not images — they stay in sync with the text)
- Screenshot placeholders: `<!-- SCREENSHOT: filename.png — description -->` above each image tag
- Run `make docs-serve` to preview locally before submitting a docs PR
