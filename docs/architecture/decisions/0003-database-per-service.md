# ADR-0003: Database per service

| Field    | Value      |
|----------|------------|
| Status   | Accepted   |
| Date     | 2026-05-22 |
| Deciders | Fred       |

## Context

Six services each need persistent state. The data model for each domain
(orders, payments, inventory, fulfillment, shipping, notifications) is
distinct, and the bounded contexts must not bleed across service boundaries.

## Considered Options

- **Database per service** — each service owns a dedicated PostgreSQL instance;
  no other service may connect to it directly.
- **Shared database, separate schemas** — one Postgres instance, each service
  uses its own schema; cross-schema joins are technically possible.
- **Shared database, shared schema** — all services read/write the same tables;
  simplifies ops, couples services tightly.

## Decision Outcome

Chose **database per service**.

A private database is the only option that makes the bounded-context boundary
physically unbreakable. Cross-service data access must travel through the
event bus (ADR-0002), which makes the coupling visible and intentional.
Shared schemas (even with schema-level isolation) allow lazy joins to creep in,
gradually eroding service autonomy.

For local dev, six Postgres containers on sequential ports (5432–5437) are
trivially managed by Docker Compose. The resource overhead is acceptable for
a research/demonstration context.

## Consequences

**Positive**
- Services can evolve their schema independently and migrate without coordination.
- No risk of one service's load or long-running transaction affecting another's
  database.
- Deployment topology (one container per service pair) maps cleanly to a
  future Kubernetes namespace-per-service layout.

**Negative / watch-outs**
- Queries that would naturally join across domains (e.g., order + payment status
  in one report) require either event-driven denormalization or an API composition layer.
- Six Postgres containers consume meaningful RAM on a developer laptop; consider
  a shared Postgres with isolated schemas if resource pressure becomes an issue
  (supersede this ADR rather than silently reverting).

## Related decisions

- [ADR-0001](0001-choreography-saga-pattern.md) — saga pattern that makes
  cross-service data access explicit via events rather than joins
