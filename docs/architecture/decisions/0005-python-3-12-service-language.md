# ADR-0005: Python 3.12 as service language

| Field    | Value      |
|----------|------------|
| Status   | Accepted   |
| Date     | 2026-05-22 |
| Deciders | Fred       |

## Context

All six domain services need an implementation language. The primary drivers
are async I/O capability (message consumption, non-blocking HTTP), ecosystem
maturity for the required integrations (AMQP, PostgreSQL, HTTP), and developer
familiarity.

## Considered Options

- **Python 3.12** — async support via `asyncio`; rich ecosystem; familiar.
- **Go** — strong concurrency primitives; excellent performance; steeper
  learning curve for this team.
- **Node.js / TypeScript** — native async; large ecosystem; introduces a
  second runtime alongside Python tooling already in the repo.
- **Java / Spring Boot** — mature microservice framework; high boilerplate and
  JVM startup overhead for a local-dev-first project.

## Decision Outcome

Chose **Python 3.12**.

`asyncio` and libraries like `aio-pika` (RabbitMQ) and `asyncpg` (PostgreSQL)
provide non-blocking I/O without the complexity of Go's goroutine model or the
JVM overhead of Spring Boot. Python 3.12 specifically brings meaningful `asyncio`
performance improvements and better error messages over 3.10/3.11.

The research/demonstration context favors developer speed and readability over
raw throughput — Python's concise syntax keeps service code focused on domain
logic rather than boilerplate.

## Consequences

**Positive**
- Consistent language across all six services; shared tooling (`pyproject.toml`,
  `pre-commit`, `pyright`).
- `asyncio` handles concurrent message consumption without threads.
- GIL limitations are not a concern for I/O-bound microservices.

**Negative / watch-outs**
- CPU-bound workloads (image processing, ML inference) would benefit from Go or
  a compiled language; those services should be considered for a language change
  if introduced.
- Python startup time is slightly higher than Go binaries, which matters for
  rapid container scaling — acceptable for local dev, worth revisiting for prod.
