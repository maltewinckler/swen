# Getting Started

SWEN can be deployed two ways. Choose the path that fits your use case:

| | Docker Compose | Bare Metal / Dev |
|---|---|---|
| **Best for** | Production / homelab | Local development, hacking |
| **Prerequisites** | Docker Engine, git | Python 3.13, Node 24, uv, PostgreSQL |
| **Effort** | ~5 minutes | ~15 minutes |
| **Hot-reload** | No | Yes (backend + frontend) |
| **Bank sync** | Yes | Yes |
| **AI classification** | Yes | Yes (optional) |

## Choose Your Path

<div class="grid cards" markdown>

-   :material-docker: **Docker Deployment** *(recommended)*

    The simplest way to run SWEN. One command brings up all five services.

    [:material-arrow-right: Docker guide](docker.md)

-   :material-code-braces: **Bare Metal / Dev**

    Run services directly on your machine. Hot-reload for fast iteration.

    [:material-arrow-right: Bare-metal guide](bare-metal.md)

</div>

## Prerequisites (both paths)

- A **FinTS Product ID** from Deutsche Kreditwirtschaft if you want live bank sync.
  You can skip this for now and add it later via the admin UI.
  [Register here →](https://www.fints.org/de/hersteller/produktregistrierung)

- For Docker: **Docker Engine 24+** with Compose V2 (`docker compose` not `docker-compose`)
- For bare metal: **Python ≥ 3.13**, **uv ≥ 0.5**, **Node.js ≥ 24**

## Resource Requirements

| Resource | Minimum | Recommended |
|---|---|---|
| RAM | 2 GB | 4 GB (for ML model) |
| Disk | 500 MB deps + DB | 2 GB (includes ML model cache ~1.5 GB) |
| CPU | Any x86-64 / ARM64 | 2+ cores |

!!! note "ARM64 / Apple Silicon"
    All images are published for both `linux/amd64` and `linux/arm64`.
    Podman users: alias `docker` → `podman` — everything works the same way.
