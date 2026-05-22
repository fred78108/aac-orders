# ADR-0012: Flask demo dashboard as a sidecar service

| Field    | Value      |
|----------|------------|
| Status   | Accepted   |
| Date     | 2026-05-22 |
| Deciders | Fred       |

## Context

The platform is demonstrated with `curl` and the RabbitMQ Management UI today.
This requires the audience to context-switch between a terminal, a browser tab,
and markdown documentation — impractical for a live demo and hard for observers
who are not comfortable with CLI tools.

A single browser-based dashboard could surface service health, queue state,
order placement, and the saga event-chain diagram in one view, lowering the
barrier to entry for non-technical stakeholders.

## Considered Options

- **No dedicated UI** — continue using `curl` + RabbitMQ Management UI + `psql`
- **Flask + Tailwind/Alpine.js sidecar** — a thin Python server that proxies
  health calls and RabbitMQ API; frontend does live polling via `fetch`
- **React/Next.js SPA** — a full frontend build pipeline with a separate API layer
- **Grafana dashboard** — instrument services with Prometheus metrics, visualise
  in Grafana

## Decision Outcome

Chose **Flask + Tailwind CDN + Alpine.js CDN sidecar**.

The demo dashboard is purely a presentation aid; it adds no business logic and
must not be confused with a production observability tool. Flask keeps the
backend trivial (three proxy routes, ~60 lines). Tailwind and Alpine.js load
from a CDN, so there is no build step, no `node_modules`, and no additional
developer toolchain to install. The entire demo can be started with
`docker compose up --build`, which is already the first step in the demo script.

React/Next.js would require a build pipeline that complicates `docker compose up`
and adds cognitive overhead. Grafana would require instrumenting six services
with Prometheus exporters, which is out of scope for a TDD baseline demo.

## Consequences

**Positive**
- Single URL to share with an audience: http://localhost:9000
- Auto-refreshing service health, RabbitMQ queue monitor, and order placement
  all visible simultaneously — no terminal required.
- The saga event-chain and compensation flows are rendered as a persistent
  visual reference rather than requiring the audience to recall the README.
- `docker compose up --build` starts the dashboard automatically alongside the
  six application services — zero extra steps.
- Can also be run standalone on the host (without Docker) by pointing env vars
  at localhost: `python demo/app.py`

**Negative / watch-outs**
- The dashboard is read-only for infrastructure data (health, queues); it cannot
  query service databases directly. DB inspection still requires `psql`.
- The saga flow diagram is static/educational — it does not animate based on
  live order state because handlers raise `NotImplementedError` (TDD baseline).
  Once handlers are implemented, queue `messages` counts in the RabbitMQ monitor
  will briefly spike during each order, providing live visual confirmation.
- Adding the demo service to `docker-compose.yml` means `docker compose up` now
  builds one additional image. The image is lightweight (~150 MB slim Python
  base) and builds quickly.

## Related decisions

- [ADR-0001](0001-choreography-saga-pattern.md) — saga pattern being visualised
- [ADR-0002](0002-rabbitmq-as-message-broker.md) — RabbitMQ data proxied by the dashboard
- [ADR-0006](0006-docker-compose-local-runtime.md) — runtime the dashboard runs within
- [ADR-0008](0008-fastapi-as-http-framework.md) — Flask chosen for the dashboard (not FastAPI) to keep it independent of the service stack
