# CI / GitHub Actions

SWEN has two automated workflows: **CI** (on every push/PR) and **Docker Publish** (on every GitHub Release).

## CI Workflow (`ci.yml`)

Triggers on every push and pull request to `main`. All 7 jobs run in parallel (no inter-job dependencies):

| Job | Purpose |
|---|---|
| `check-lockfile` | Verify `uv.lock` consistency |
| `lint-backend` | Ruff lint + format check |
| `lint-frontend` | ESLint + TypeScript check |
| `test-backend-unit` | Unit tests (Python 3.13) |
| `test-backend-integration` | Integration tests with Testcontainers |
| `test-frontend` | Vitest tests |
| `build-frontend` | Production Vite build |

### Jobs

All jobs run on `ubuntu-latest` with Python 3.13 (backend) or Node.js 24 (frontend).

#### `check-lockfile`

```yaml
run: uv lock --check
```

Verifies that `uv.lock` is consistent with all `pyproject.toml` files. Fails fast if someone added a dependency but forgot to commit the updated lockfile.

#### `lint-backend`

Runs **Ruff** in check mode and format check via `uv run`:

```bash
uv run ruff check services/backend/src/
uv run ruff format --check services/backend/src/
```

#### `lint-frontend`

```bash
npx @tanstack/router-cli generate   # Ensure route tree is up to date
npm run lint                        # ESLint
npx tsc --noEmit                    # TypeScript type check
```

#### `test-backend-unit`

Runs the unit test suite (no Docker required):

```bash
uv run pytest services/backend/tests/swen/unit/ services/backend/tests/swen_identity/unit/ -v
```

#### `test-backend-integration`

Runs integration tests using Testcontainers. Requires Docker-in-Docker — GitHub's `ubuntu-latest` runner provides Docker out of the box.

Hardcoded test secrets are injected so the app starts correctly without real credentials:

```yaml
env:
  RUN_INTEGRATION: "1"
  ENCRYPTION_KEY: "X6gejiP08L9cH4nW4bQk8aGo961x2rhGE40jOg67VwU="
  JWT_SECRET_KEY: "test-jwt-secret-for-ci"
  POSTGRES_PASSWORD: "test-password-not-used"
```

Runs integration tests across all test directories:

```bash
uv run pytest services/backend/tests/swen/integration/ \
  services/backend/tests/swen_identity/integration/ \
  services/backend/tests/cross_domain/integration/ \
  services/backend/tests/cross_domain/e2e/ -v
```

#### `test-frontend`

```bash
npx @tanstack/router-cli generate   # Ensure route tree is up to date
npm run test                        # Vitest
```

#### `build-frontend`

Verifies the production Vite build succeeds:

```bash
npx @tanstack/router-cli generate   # Ensure route tree is up to date
npm run build
```

---

## Docker Publish Workflow (`docker-publish.yml`)

Triggers when a **GitHub Release** is published.

### Matrix Strategy

Three images are built in parallel (`fail-fast: false` — a failed ML build doesn't cancel the others):

| Service | Image | Dockerfile |
|---|---|---|
| `backend` | `maltewin/swen-backend` | `services/backend/Dockerfile` |
| `frontend` | `maltewin/swen-frontend` | `services/frontend/Dockerfile` |
| `ml` | `maltewin/swen-ml` | `services/ml/Dockerfile` |

### Steps

1. **Semver validation** — Ensures the tag matches `vX.Y.Z` before doing any work
2. **Log in to Docker Hub** — Uses `DOCKERHUB_USERNAME` + `DOCKERHUB_TOKEN` repository secrets
3. **`docker/metadata-action`** — Generates tags: `X.Y.Z`, `X.Y`, `X`, `latest`
4. **`docker/build-push-action`** — Builds the image with GHA layer cache, pushes to Docker Hub

### Produced Tags

For a `v1.2.3` release, each image gets four tags:

```
maltewin/swen-backend:1.2.3
maltewin/swen-backend:1.2
maltewin/swen-backend:1
maltewin/swen-backend:latest
```

### GHA Cache

Each service has its own cache scope to prevent cache thrashing:

```yaml
cache-from: type=gha,scope=${{ matrix.service }}
cache-to:   type=gha,scope=${{ matrix.service }},mode=max
```

---

## Dependabot (`dependabot.yml`)

Dependabot runs **weekly** (Mondays) and opens grouped PRs:

| Ecosystem | Directory | Group Name | Ignored |
|---|---|---|---|
| `pip` | `/services/backend` | `python-dependencies` | — |
| `npm` | `/services/frontend` | `npm-dependencies` | ESLint & `@eslint/js` major versions |
| `github-actions` | `/` | `github-actions-dependencies` | — |

Grouped PRs mean you get one `[pip] Bump dependencies` PR per week rather than dozens of individual ones.

---

## Additional Workflows

### Documentation (`docs.yml`)

Triggers on pushes to `docs/**` or `zensical.toml`, or via `workflow_dispatch`. Builds the MkDocs site with Zensical and deploys to **GitHub Pages**.

### PR Title Check (`pr-title.yml`)

Triggers on `opened`, `edited`, `synchronize`, `reopened` for PRs to `main`. Validates that PR titles match the conventional commit format:

```
[Type] Description
```

Valid types: `[Feat]`, `[Fix]`, `[Refactor]`, `[Docs]`, `[Test]`, `[Chore]`, `[Perf]`, `[Style]`, `[CI]`, `[Deps]`, `[Security]`, `[Hotfix]`, `[Revert]`, `[WIP]`.
