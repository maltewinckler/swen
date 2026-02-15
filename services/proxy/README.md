# SWEN Docker Setup

Self-hosted deployment of SWEN (Secure Wallet & Expense Navigator) using Docker.

## Prerequisites

- Docker with Compose V2 (or Podman — alias `docker` to `podman`)
- A reverse proxy (nginx, Caddy, Traefik, etc.) — or use the [built-in Caddy](#built-in-caddy)

## Deployment

### 1. Clone and Configure

```bash
git clone https://github.com/maltewinckler/swen.git
cd swen
cp config/.env.example config/.env
```

### 2. Generate Secrets

```bash
docker compose build backend
docker compose run --rm --no-deps backend swen secrets generate
```

### 3. Edit Configuration

Edit `config/.env` with the generated secrets and your settings:

```bash
ENCRYPTION_KEY=<generated-key>
JWT_SECRET_KEY=<generated-key>
POSTGRES_PASSWORD=<generated-key>

# Your domain
API_CORS_ORIGINS=https://swen.example.com
API_COOKIE_SECURE=true

# Frontend: Allow access from your domain (required for Vite preview server)
VITE_ALLOWED_HOSTS=swen.example.com
```

### 4. Configure Your Reverse Proxy

Route these paths to the Docker containers:

| Route | Target (host proxy) | Target (Docker proxy) |
|-------|---------------------|----------------------|
| `/api/*` | `http://localhost:8000` | `http://swen-backend:8000` |
| `/health` | `http://localhost:8000` | `http://swen-backend:8000` |
| `/*` | `http://localhost:3000` | `http://swen-frontend:3000` |

> Use `localhost` if your proxy runs on the host. Use container names if your proxy runs in Docker on the same network (`swen-network`).

**Note:** Set 6-minute timeout for `/api/*` (bank sync waits for TAN input).

See `services/proxy/examples/` for nginx and Traefik reference configurations.

### 5. Deploy

```bash
# Create data directory with correct permissions
mkdir -p data && sudo chown 65532:65532 data

# Start
docker compose up -d --build

# Verify
curl https://swen.example.com/health
```

## Built-in Caddy

For local testing purposes, we have a proxy built into SWEN We recommend to use your own reverse proxy in production.

```bash
docker compose --profile proxy up -d --build
```

This routes `http://localhost/api/*` → backend and `http://localhost/*` → frontend.

### HTTPS with Caddy

Edit `services/proxy/Caddyfile` — replace `:80` with your domain:

```caddyfile
swen.example.com {
    handle /api/* {
        reverse_proxy backend:8000 {
            transport http {
                response_header_timeout 360s
            }
        }
    }
    handle /health {
        reverse_proxy backend:8000
    }
    handle {
        reverse_proxy frontend:3000
    }
}
```
