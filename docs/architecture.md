# Architecture & Development Practices

This document outlines the software architecture and development practices used in SWEN.

## Core Principles

SWEN follows a **Domain-Driven Design (DDD)** approach combined with **Hexagonal Architecture** (Ports & Adapters) and **CQRS** (Command Query Responsibility Segregation). These patterns work together to create a hopefully maintainable, testable, and flexible codebase.

## Layer Structure

The backend is organized into four distinct layers:

- **Domain** — Core business logic, pure Python with no framework dependencies
- **Application** — Use cases and orchestration (commands, queries, services)
- **Infrastructure** — External integrations (database, banking APIs, AI services)
- **Presentation** — User-facing interfaces (REST API, CLI)

Dependencies point **inward only**: outer layers depend on inner layers, never the reverse. Infrastructure implements domain interfaces through dependency inversion.

## Domain-Driven Design (DDD)

### Bounded Contexts

The domain is divided into cohesive bounded contexts, each modeling a distinct area of the business:

- **Accounting** — Double-entry bookkeeping
- **Banking** — Bank connections and transaction data
- **Integration** — Bridges banking and accounting domains
- **Security** — Credential encryption and storage
- **User** — User preferences and settings

Each context encapsulates its own entities, value objects, aggregates, repositories, and domain services.

### Ubiquitous Language

We maintain a [ubiquitous language glossary](./ubiquitous_language.md) to ensure consistent terminology across code, documentation, and conversations.

### Value Objects vs Entities

**Value Objects** are immutable and compared by their attributes (e.g., an IBAN or money amount). **Entities** have identity and lifecycle, compared by their unique ID (e.g., an Account or Transaction).

## Hexagonal Architecture (Ports & Adapters)

The domain defines **ports**—abstract interfaces describing what capabilities it needs (e.g., "connect to a bank" or "persist an account"). The infrastructure layer provides **adapters**—concrete implementations of these ports.

This allows swapping implementations without changing business logic. For example, the banking port can be implemented by a FinTS adapter today and a PSD2 adapter tomorrow (if regulations allow it lol).

### Anti-Corruption Layer

External libraries are wrapped in adapters that translate between their data structures and our domain model. This protects the domain from breaking changes in third-party dependencies and if changes are necessary, they are contained within this layer.

## CQRS (Command Query Responsibility Segregation)

The application layer separates operations into:

- **Commands** — Represent intent to change state (create, update, delete)
- **Queries** — Retrieve data without side effects

Queries return **DTOs** (Data Transfer Objects) rather than domain entities, decoupling the API contract from the internal domain model. We are not 100% sure yet if this is overengineering or a good maintainability trait.

## Repository Pattern

Repositories abstract data access behind interfaces defined in the domain. The domain specifies *what* data operations are needed; infrastructure decides *how* to implement them.

All repositories are scoped to the current user via a `UserContext`, ensuring automatic data isolation between users.

## Dependency Injection

Dependencies are injected rather than instantiated directly. The presentation layer wires everything together, making it easy to:

- Swap implementations (e.g., SQLite for development, PostgreSQL for production)
- Test with mocks
- Trace the dependency graph

## Testing Strategy

Tests are organized to mirror the layer structure:

- **Unit tests** — Test domain logic in isolation with mocked dependencies
- **Integration tests** — Test with real database and full request/response cycles

## Key Patterns Summary

- **Bounded Contexts** — Organize business concepts into cohesive modules
- **Ports & Adapters** — Decouple domain from external systems
- **Repository** — Abstract data access behind interfaces
- **CQRS** — Separate read and write operations
- **DTOs** — Decouple API contracts from domain model
- **Anti-Corruption Layer** — Protect domain from external library changes
- **Dependency Injection** — Enable flexible wiring and testing
- **User Context** — Ensure multi-tenancy and data isolation

## Diagrams

We have experimented with some AI generated, curated PlantUML diagrams which are available in `docs/diagrams/`:

- **system-overview.wsd** — High-level system components (frontend, backend, database, external services)
- **layers.wsd** — Hexagonal architecture with ports and adapters
- **bounded-contexts.wsd** — Domain contexts and their relationships
- **import-flow.wsd** — Transaction import sequence (bank → accounting)
- **accounting.wsd** — Accounting domain class diagram
- **banking.wsd** — Banking domain class diagram

## Further Reading

- [Ubiquitous Language](./ubiquitous_language.md) — Shared vocabulary
- [Deduplication Logic](./deduplication_logic.md) — How duplicate transactions are handled
