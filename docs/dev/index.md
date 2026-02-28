# Developer Guide

Welcome to the SWEN developer documentation.

<div class="grid cards" markdown>

-   :material-layers: **[Architecture](architecture.md)**

    Domain-Driven Design, hexagonal architecture, CQRS, bounded contexts. Start here.

-   :material-server: **[Backend](backend.md)**

    FastAPI app structure, DI, JWT auth, settings, key services.

-   :material-react: **[Frontend](frontend.md)**

    React 19, TanStack Router/Query, Zustand, Radix UI, auth flow.

-   :material-brain: **[ML Service](ml-service.md)**

    FastAPI ML service internals, lifespan, shared infrastructure, training data flow.

-   :material-database: **[Database](database.md)**

    PostgreSQL schema, two databases, CLI init, key tables.

-   :material-test-tube: **[Testing](testing.md)**

    Test pyramid, Testcontainers, markers, CI policy.

-   :material-github: **[CI / GitHub Actions](ci.md)**

    All workflows explained: CI, Docker publish, Dependabot.

-   :material-tag: **[Release Process](releasing.md)**

    How to cut a release, what tags are created, how to update a running deployment.

</div>

## Quick Links

- **Run all tests:** `make test`
- **Run backend:** `make backend`
- **Architecture diagram:** [architecture.md](architecture.md#hexagonal-architecture-ports-adapters)
- **API docs (Swagger):** `http://localhost:8000/docs` (when running locally)
- **Test README:** see [Testing](testing.md)
