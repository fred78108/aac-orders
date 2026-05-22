# ADR-0009: Hexagonal (ports and adapters) internal service layout

| Field    | Value      |
|----------|------------|
| Status   | Accepted   |
| Date     | 2026-05-22 |
| Deciders | Fred       |

## Context

Each of the six microservices must deal with three distinct types of I/O:
HTTP (inbound for order-service), messaging via RabbitMQ (inbound events,
outbound events), and a PostgreSQL database. Without a deliberate internal
structure, domain logic tends to leak into I/O code and vice-versa, making
services hard to test and reason about.

## Considered Options

- **Hexagonal / ports and adapters** — a `domain/` layer with no I/O
  dependencies, surrounded by adapter modules (`api/`, `events/`, `db/`)
  that translate between the domain and infrastructure.
- **Layered MVC** — controllers → services → repositories in a strict
  horizontal stack; no hard separation between domain and infrastructure.
- **Flat layout** — all code at the service root; simple for small services
  but collapses as complexity grows.

## Decision Outcome

Chose **hexagonal layout** with the following module structure per service:

```
services/<name>/
  domain/       # pure Python — dataclasses, enums, business rules; no I/O
  api/          # HTTP adapter  (FastAPI routers)
  events/       # messaging adapters (handlers = inbound, publishers = outbound)
  db/           # persistence adapter (repository classes, SQLAlchemy models)
  app.py        # wires adapters into the FastAPI app
  settings.py   # reads environment variables
```

`domain/` deliberately has no imports from `api/`, `events/`, `db/`, or any
third-party I/O library. Adapters import from `domain/`; `domain/` never
imports from adapters. This makes domain logic unit-testable without any
infrastructure running.

## Consequences

**Positive**
- Domain logic is testable with plain `pytest` — no database, no broker, no HTTP client required.
- Adding a new adapter (e.g., a gRPC endpoint) only touches `api/`; `domain/` is untouched.
- The layout is uniform across all six services, reducing cognitive overhead when switching between them.

**Negative / watch-outs**
- More directories than a flat layout; can feel over-engineered for very small services.
- Care is needed to keep `domain/` pure — it is easy to accidentally import SQLAlchemy
  models or Pydantic schemas into domain code.  Use linting or import guards if drift is detected.

## Related decisions

- [ADR-0001](0001-choreography-saga-pattern.md) — `events/handlers.py` and `events/publishers.py` implement the saga wiring
- [ADR-0008](0008-fastapi-as-http-framework.md) — `api/routes.py` is the HTTP adapter
- [ADR-0011](0011-sqlalchemy-asyncio-persistence.md) — `db/repository.py` is the persistence adapter
