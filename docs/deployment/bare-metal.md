# Bare Metal / Dev Setup

Run SWEN directly on your machine without Docker. This is the best approach for development — you get hot-reload on both the backend and frontend.

!!! warning "Not for production"
    The bare-metal setup is intentionally convenient and insecure (open registration, weak default secrets). Use [Docker Compose](docker.md) for any real deployment.

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | ≥ 3.13 | [python.org](https://www.python.org/) or `pyenv` |
| uv | ≥ 0.5 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | ≥ 24 | [nodejs.org](https://nodejs.org/) or `fnm` / `nvm` |
| PostgreSQL | ≥ 18 | System package or `docker run postgres:18-alpine` |

## 1 · Clone and Install

```bash
git clone https://github.com/maltewinckler/swen.git
cd swen
make install
```

`make install` calls `uv sync` (Python workspace) and `npm install` (frontend) in one step.

## 2 · Configure Environment

```bash
swen setup
```

Choose **Development** when prompted. The wizard generates `config/.env.dev` with all secrets pre-filled and sensible local defaults (`POSTGRES_HOST=localhost`, `REGISTRATION_MODE=open`, etc.).

!!! tip
    You can also copy the example manually and edit by hand:
    ```bash
    cp config/.env.example config/.env.dev
    ```

## 3 · Initialise the Database

Make sure PostgreSQL is running, then:

```bash
make db-init
```

This creates the `swen` and `swen_ml` schemas (tables, indexes, initial data).

## 4 · Run the Services

Open three terminals (or use `tmux`):

=== "Terminal 1 — Backend"

    ```bash
    make backend
    # → http://127.0.0.1:8000
    # → API docs at http://127.0.0.1:8000/docs
    ```

=== "Terminal 2 — Frontend"

    ```bash
    make frontend
    # → http://localhost:5173 (Vite HMR)
    ```

=== "Terminal 3 — ML (optional)"

    ```bash
    make ml
    # → http://127.0.0.1:8001
    # First run downloads the model (~1.5 GB)
    ```

Then open **http://localhost:5173** in your browser.

## Demo Data

To populate realistic demo data for development:

```bash
make seed-demo
```

This creates a demo user (`demo@example.com` / `demo`) with sample accounts, bank accounts, and ~200 transactions in various states.

## Makefile Reference

Run `make help` for the full list. Common targets:

| Command | What it does |
|---|---|
| `make install` | Install all deps (Python + Node) |
| `make backend` | Start backend on :8000 |
| `make frontend` | Start frontend on :5173 |
| `make ml` | Start ML service on :8001 |
| `make test` | Run the full test suite |
| `make lint` | Ruff + ESLint |
| `make format` | Auto-format Python (Ruff) |
| `make db-init` | Create DB schema |
| `make db-reset` | **Drop + recreate** DB (destructive!) |
| `make seed-demo` | Load demo transactions |
| `make secrets` | Print newly generated secrets |
| `make docs-serve` | Serve this documentation locally |

## Port Reference

| Service | URL | Notes |
|---|---|---|
| Frontend | `http://localhost:5173` | Vite dev server, hot-reload |
| Backend | `http://127.0.0.1:8000` | FastAPI, auto-reload on save |
| Backend API docs | `http://127.0.0.1:8000/docs` | Swagger UI |
| ML service | `http://127.0.0.1:8001` | Only needed for AI classification |
| PostgreSQL | `localhost:5432` | Direct DB access |

## Environment Files

| File | Used by | DB host |
|---|---|---|
| `config/.env.dev` | Bare metal (Makefile) | `localhost` |
| `config/.env` | Docker Compose | `postgres` (service name) |

SWEN's pydantic-settings loader automatically picks the right file — `.env.dev` when `APP_ENV=development` (the Makefile default), `.env` otherwise.
