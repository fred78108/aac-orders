# ADR-0008: FastAPI as HTTP framework

| Field    | Value      |
|----------|------------|
| Status   | Accepted   |
| Date     | 2026-05-22 |
| Deciders | Fred       |

## Context

Each microservice needs a lightweight HTTP layer for two purposes: the
order-service must expose `POST /orders` as the single synchronous entry
point into the saga, and every service needs a `/health` endpoint for
Docker Compose liveness checks.

The framework must be comfortable with Python 3.12's `async`/`await` since
all I/O (database, RabbitMQ) is async throughout the stack.

## Considered Options

- **FastAPI** — async-native, OpenAPI generation, Pydantic-based request
  validation, actively maintained.
- **Flask** — mature, synchronous by default; async support is bolted on and
  less idiomatic.
- **aiohttp** — low-level async HTTP server/client; no built-in validation or
  OpenAPI; more boilerplate.

## Decision Outcome

Chose **FastAPI**.

Its async-first design aligns with the rest of the stack (aio-pika, asyncpg,
SQLAlchemy asyncio). Automatic OpenAPI docs give each service a self-describing
HTTP contract at no extra cost. Pydantic request/response models integrate
naturally with the domain layer. The `APIRouter` pattern maps cleanly to the
`api/routes.py` module in each service's hexagonal layout (ADR-0009).

## Consequences

**Positive**
- Async handlers are idiomatic, not an afterthought.
- OpenAPI spec generated automatically from route annotations.
- Pydantic validation keeps malformed requests out of the domain layer.
- `APIRouter` allows each service to compose routes independently.

**Negative / watch-outs**
- Pydantic v2 (bundled with FastAPI ≥ 0.100) has breaking changes from v1;
  prefer `model_config` and `model_validate` over legacy aliases from the start.
- Startup/shutdown lifespan events (for connecting to RabbitMQ and the DB)
  require the `lifespan` context-manager pattern introduced in FastAPI 0.93 —
  do not use the deprecated `on_event` decorator.

## Related decisions

- [ADR-0005](0005-python-3-12-service-language.md) — async Python requirement
- [ADR-0009](0009-hexagonal-internal-service-layout.md) — internal layout that houses `api/routes.py`
- [ADR-0011](0011-sqlalchemy-asyncio-persistence.md) — async persistence layer used alongside FastAPI
