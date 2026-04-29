# Dev Environment Setup

This page describes how to set up a full local development environment for contributing to SWEN.

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | ≥ 3.13 | [python.org](https://www.python.org/) or `pyenv install 3.13` |
| uv | ≥ 0.5 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | ≥ 24 | [nodejs.org](https://nodejs.org/) or `fnm install 24` |
| git | any | system package |
| Docker (or Podman) | any | [docs.docker.com](https://docs.docker.com/get-docker/) |
| PostgreSQL | ≥ 18 | Docker `postgres:18-alpine` or system package |

## 1 · Clone and Install

```bash
git clone https://github.com/maltewinckler/swen.git
cd swen
make install
```

This runs `uv sync` (Python workspace: backend + ML + contracts) and `npm install` (frontend) in one step.

## 2 · Configure Environment

```bash
cp config/.env.example config/.env.dev
```

The example file ships with safe defaults for local development. Only these keys typically need changing:

```bash
# If your local Postgres uses a different password
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
```

Relaxed security settings are pre-enabled in the example (`API_COOKIE_SECURE=false`, `REGISTRATION_MODE=open`).

## 3 · Start Postgres

=== "Docker (easiest)"

    ```bash
    docker run -d \
      --name swen-postgres \
      -e POSTGRES_PASSWORD=postgres \
      -p 5432:5432 \
      postgres:18-alpine
    ```

=== "System PostgreSQL"

    Ensure PostgreSQL is running and accessible at `localhost:5432`. Create the user `postgres` with password `postgres` (or adjust `.env.dev`).

## 4 · Initialise the Database

```bash
make db-init
```

## 5 · Install Pre-commit Hooks (recommended)

```bash
make pre-commit-install
```

This installs Ruff, detect-secrets, and end-of-file fixers as pre-commit hooks that run before every commit.

## 6 · Run the Services

```bash
# Terminal 1 — backend (port 8000, hot-reload)
make backend

# Terminal 2 — frontend (port 5173, Vite HMR)
make frontend

# Terminal 3 — ML service (port 8001, optional)
make ml
```

Open **http://localhost:5173**, register (first user = admin), and start exploring.

## 7 · Load Demo Data (optional)

```bash
make seed-demo
```

Creates `demo@example.com` / `demo` with ~200 sample transactions.

## Running Tests

### ⚠️ Podman Users: Required Configuration

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

```bash
# All tests
make test

# Backend only (unit + integration)
make test-backend

# ML service
make test-ml

# With coverage report
make test-cov
```

### Additional Podman Configuration

For running the development database container with Podman:

```bash
export TESTCONTAINERS_RYUK_DISABLED=true
```

## Common Issues

| Problem | Fix |
|---|---|
| `uv sync` fails on `geldstrom` | Ensure git is installed and GitHub is reachable |
| Port 5432 already in use | Stop local Postgres or change `POSTGRES_PORT` |
| Frontend blank screen | Check browser console — may be a CORS / backend not running issue |
| `db-init` fails | Verify Postgres is running and credentials match `.env.dev` |
