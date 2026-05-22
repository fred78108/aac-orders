# ADR-0010: Monorepo with shared library

| Field    | Value      |
|----------|------------|
| Status   | Accepted   |
| Date     | 2026-05-22 |
| Deciders | Fred       |

## Context

Six services share a common vocabulary: domain event dataclasses
(`OrderCreatedEvent`, `PaymentCapturedEvent`, etc.), RabbitMQ connection
abstractions, SQLAlchemy async session helpers, and a base settings class.
A decision is needed on how to distribute this shared code.

## Considered Options

- **Monorepo with `services/shared/` installable library** — all services and
  the shared library live in one repository; `shared` is a Python package
  discovered by setuptools and installed editably in the dev venv.
- **Copy-per-service** — shared code is duplicated into each service directory
  and kept in sync manually.
- **Separate shared library repository** — `shared` lives in its own repo,
  versioned and published to a package registry (PyPI or private).

## Decision Outcome

Chose **monorepo with `services/shared/` as an installable package**.

For a learning/research project this avoids the overhead of a package registry
while keeping all code in one place. Changes to shared event schemas are
immediately visible to all services without a publish-install cycle. The
`pyproject.toml` at the project root uses `[tool.setuptools.packages.find]
where = ["services"]` so that `shared`, `order`, `payment`, etc. are all
importable after `pip install -e .` in the dev venv.

In Docker, each service's `Dockerfile` uses the project root as build context
and copies `services/shared` to `/app/shared` alongside the service package.

## Consequences

**Positive**
- Single checkout; all services and shared code visible together.
- Event schema changes are atomic across the whole system — no version skew.
- Dev tooling (ruff, mypy, pytest) covers everything in one invocation.

**Negative / watch-outs**
- `services/shared/` is a coupling point; breaking changes affect all services
  simultaneously. Treat it as a stable API: add fields, don't remove or rename.
- If services are ever split into separate repos, a migration to a versioned
  package will be needed.
- Docker build times grow slightly because the full repo is the build context;
  a `.dockerignore` should exclude `.venv/`, `docs/`, `tests/`, and generated files.

## Related decisions

- [ADR-0006](0006-docker-compose-local-runtime.md) — build context strategy
- [ADR-0001](0001-choreography-saga-pattern.md) — shared event types are the lingua franca of the saga
