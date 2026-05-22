# ADR-0011: SQLAlchemy asyncio + asyncpg as persistence layer

| Field    | Value      |
|----------|------------|
| Status   | Accepted   |
| Date     | 2026-05-22 |
| Deciders | Fred       |

## Context

Each service owns a PostgreSQL database and needs an async-compatible
persistence layer that works inside FastAPI's async event loop and alongside
aio-pika consumers. The choice spans the ORM/query layer and the low-level
driver.

## Considered Options

- **SQLAlchemy 2 asyncio + asyncpg** — SQLAlchemy's `AsyncSession` with the
  `asyncpg` driver; full ORM and Core query API available.
- **Raw asyncpg** — direct async PostgreSQL driver with no ORM; maximum
  control, maximum boilerplate.
- **Tortoise ORM** — async-native Django-style ORM; simpler setup but smaller
  ecosystem and less mature migration tooling.
- **databases (encode/databases)** — thin async query layer over SQLAlchemy
  Core; limited and no longer actively maintained.

## Decision Outcome

Chose **SQLAlchemy 2 asyncio + asyncpg**.

SQLAlchemy 2's native `AsyncSession` and `async_sessionmaker` are
production-ready and eliminate the impedance mismatch that plagued the 1.x
async extensions. asyncpg is the fastest PostgreSQL driver for Python. Together
they give full ORM capabilities (relationships, lazy/eager loading with
`selectinload`) and access to Core expressions when raw SQL is preferable —
all without blocking the event loop.

The shared `db.py` module exposes a `make_session_factory(url)` helper and a
`Base` declarative class so each service's `db/repository.py` has a consistent
starting point.

## Consequences

**Positive**
- Full async throughout: no `run_sync` wrappers needed.
- Alembic migration support works with the same `Base` metadata.
- ORM and Core queries available in the same session; services can start with
  ORM and drop to Core for performance-sensitive paths.
- asyncpg is significantly faster than psycopg2 for high-throughput scenarios.

**Negative / watch-outs**
- SQLAlchemy asyncio requires `expire_on_commit=False` on the session factory
  to avoid lazy-load errors after `session.commit()` — the shared helper sets
  this by default.
- ORM model classes (SQLAlchemy `Base` subclasses) must live in `db/` and must
  not leak into `domain/` — domain models use plain dataclasses per ADR-0009.
  Repositories are responsible for mapping between the two.
- `async_scoped_session` is needed if sessions must be shared across concurrent
  tasks; per-request sessions (the default pattern) avoid this complexity.

## Related decisions

- [ADR-0003](0003-database-per-service.md) — one PostgreSQL database per service
- [ADR-0009](0009-hexagonal-internal-service-layout.md) — persistence lives in `db/repository.py`, isolated from domain
- [ADR-0008](0008-fastapi-as-http-framework.md) — sessions injected via FastAPI dependency injection
