# SWEN - Secure Wallet & Expense Navigator

SWEN is a personal banking application to view, categorize, and analyze your bank transactions. It comes with built in support for German FinTS/HBCI bank to automatically sync your bank transactions.

While searching for a personal bookkeeping app where we do not have to give our very personal data (e.g. banking transactions and even permanent 2FA access to the account), we quickly found that there are not many single-service alternatives available (and it seemed like a good opportunity to learn some domain driven design :-)).

SWEN allows you to:
* Track and organize your transactions in a double-entry bookkeeping system;
* Define categories (in the double entry bookkeeping language `accounts`) yourself or from a template;
* Connect to your FINTS/HBCI enabled bank (find a maybe outdated list [under subsembly.com](https://subsembly.com/banken.html))and automatically import your transactions with a solid duplicate detection.
* Assign your income, expenses, and internal transfers automatically to the respective income/expense/asset accounts using selfhosted LLMs (based on ollama; still in MVP phase, want to experiment with something better suited for this purpose in the future.)

> **Version Note**: I consider SWEN to be in version 0.1. There are still important parts missing which I decided to cut short for MVP. This includes among others other TAN methods than the decoupled app 2FA (e.g. SecureGo App, ING App, DKB App, ...). Moreover, the TAN process has not been tested for *all* banks. Hence, if you find an issue, please create an issue :-).

> **Important Note**: In order to use the bank connection functionality, you need to register your deplyment at the Deutsche Kreditwirtschaft and get a product id. This is a mandatory step for a few years now. It usually works quite quickly. Register your deployment [here](https://www.fints.org/de/hersteller/produktregistrierung). Additionally to the registration key, you will receive a `.csv` file with all the bank-related information. This must be placed in `config/fints_institute.csv` and is parsed automatically by the backend.

> **AI Disclaimer**: The frontend is almost completely AI generated. I just have no clue about React and Type Script. Therefore, be cautious until it is thoroughly reviewed. Moreover, Docstrings in python classes are also AI enhanced.

> **Dependencies Note**: The backend depends on a python package [geldstrom](https://github.com/maltewinckler/geldstrom) which is *greatly* inspired by the OG FinTS implementation [python-fints](https://github.com/raphaelm/python-fints) with a reduced functionality set for SWEN. This is still under development.

## Getting Started (Local Development)

Below you can find two different deployment guides: One for the production usage with Docker and one for barebone install, best suited for development and testing purposes.

Both ways require roughly:
- **RAM**: 4 GB minimum, 8 GB+ recommended if using Ollama with AI models
- **Disk**: ~500 MB for dependencies, plus space for your database (marginal)

Both installation methods use `.env` files in the `config/` directory:

| File | Used by | `POSTGRES_HOST` | `OLLAMA_HOST` |
|---|---|---|---|
| `config/.env.dev` | Bare metal (Makefile) | `localhost` | `localhost` |
| `config/.env` | Docker Compose | `postgres` | `ollama` |


## Docker Compose

We will describe the steps for a docker deployment with a reverse proxy. You can choose to use our built in Caddy service, but we recommend to built it into your own production reverse proxy. To make it easier, we have put some example files to `services/proxy/examples/`. **Note**: These are AI generated and we have not (yet) tested if they work, so please be cautious.

### Prerequisites

- Docker with Compose V2 (or Podman — alias `docker` to `podman`)
- A reverse proxy (nginx, Caddy, Traefik, etc.) or use our built in one for quick testing
- The registration key and `fints_institute.csv` at Deutsche Kreditwirtschaft for bank sync ([here](https://www.fints.org/de/hersteller/produktregistrierung)).

### Generate Secrets

```bash
docker compose build backend
docker compose run --rm --no-deps backend swen secrets generate
```

### Edit Configuration

Copy and edit the environment file:

```bash
cp config/.env.example config/.env
```

Edit `config/.env` with your values:

```bash
# Required secrets (from secrets generate command)
ENCRYPTION_KEY=<generated-key>
JWT_SECRET_KEY=<generated-key>
POSTGRES_PASSWORD=<generated-key>

# Fints credential
FINTS_PRODUCT_ID=<your-deutsche-kreditwirtschaft-product-id>

# Docker networking (use service names, not localhost!)
POSTGRES_HOST=postgres
OLLAMA_HOST=ollama

# Your domain and security settings
API_COOKIE_SECURE=true
API_CORS_ORIGINS=https://swen.example.com
```

### Configure Your Reverse Proxy

Route these paths to the Docker containers:

- `/api/*`: `http://swen-backend:8000`
- `/health`: `http://swen-backend:8000`
- `/*`: `http://swen-frontend:3000`

If your proxy runs on the host (not in Docker), use `localhost` instead of container names.

### Deploy

```bash
# If you have configured your own proxy, run
docker compose up -d
# If not run and you want to use our built in proxy
docker compose --profile proxy up -d
```

> **Note:** The LLM is automatically downloaded on first startup. To pre-download it:
> `docker exec swen-ollama ollama pull qwen2.5:1.5b`

> **Note**: The proxy built into SWEN is mostly for testing purposes and a quick setup in a fresh homelab VM. We recommend to use your own reverse proxy in production. Moreover, We use port 8080/8443 by default for rootless container compatibility. If you need ports 80/443, run the proxy deployment as root.

## Bare Metal

This guide covers running SWEN without Docker, directly on your machine. This is not made to run in a prod environment! Just for a quick demo, development, ...

### Prerequisites

* `Python >= 3.10` (backend)
* `Poetry >= 2` (Python Project Management)
* `Node.js >= 24` (frontend)
* `PostgreSQL >= 18` (database)
* `Ollama` (*Optional* but required for LLM categorization)

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-username/swen.git
   cd swen
   ```

2. **Install all dependencies**

   ```bash
   make install
   ```

   This installs both Python (via Poetry) and Node.js (via npm) dependencies.

3. **Create your configuration**

   ```bash
   cp config/.env.example config/.env.dev
   ```

   Then edit `config/.env.dev` and set your FinTS product ID:

   ```bash
   FINTS_PRODUCT_ID=<your-deutsche-kreditwirtschaft-product-id>
   ```

   The other defaults (encryption key, JWT secret) work fine for **local** development but are **not** safe for prod use.

### Running the Application

SWEN consists of three services. Run each in a separate terminal:

   * `make ollama`: Starts Ollama server (optional, for AI features)
   * `make backend`: Starts the backend API on http://127.0.0.1:8000
   * `make frontend`: Starts the React dev server on http://localhost:3000

Then open http://localhost:3000 in your browser.

### Makefile Reference

Run `make help` for a full list of commands. Here are the most common:

- `make install`: Install all dependencies
- `make backend`: Start the backend API server
- `make frontend`: Start the frontend dev server
- `make ollama`: Start Ollama for AI features
- `make test`: Run all tests
- `make lint`: Run linters (backend + frontend)
- `make build`: Build frontend for production
- `make clean`: Remove build artifacts
- `make db-init`: Initialize database tables
- `make db-reset`: Reset the database (WARNING: deletes all data)
