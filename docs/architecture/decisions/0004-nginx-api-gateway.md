# ADR-0004: Nginx as API gateway

| Field    | Value      |
|----------|------------|
| Status   | Accepted   |
| Date     | 2026-05-22 |
| Deciders | Fred       |

## Context

The system exposes a single synchronous HTTP entry point to clients. All
async choreography happens internally; externally, customers interact via
standard HTTP. A gateway is needed to terminate TLS (in production), route
requests, and prevent direct client access to internal services.

## Considered Options

- **Nginx** — lightweight reverse proxy; configuration-as-code via `nginx.conf`.
- **Kong** — API gateway with plugin ecosystem (auth, rate-limiting, observability);
  heavier to configure locally.
- **Traefik** — Docker-native reverse proxy with automatic service discovery;
  more configuration magic than desired for an explicit architecture demo.
- **Direct service exposure** — expose `order-service` on port 8001 with no
  gateway; simplest, but eliminates the architectural boundary.

## Decision Outcome

Chose **Nginx**.

The gateway's role in this system is narrow: route `POST /orders` (and future
paths) to `order-service` at port 8001. Nginx handles this with a few lines of
configuration and adds no new languages or plugin frameworks to learn. The
`nginx.conf` file is version-controlled and human-readable, which supports the
architecture-as-code demonstration goal.

Kong and Traefik are appropriate when the gateway is a product (complex routing,
auth plugins, rate limiting). Here it is structural glue — Nginx is sufficient.

## Consequences

**Positive**
- Single, explicit `nginx.conf` makes gateway routing visible and auditable.
- Official Docker image; zero extra dependencies.
- Trivially replaceable (update one line in Docker Compose) if requirements change.

**Negative / watch-outs**
- Nginx has no built-in request tracing or per-route metrics; add a sidecar or
  upstream observability tool if that becomes necessary.
- Advanced gateway features (JWT validation, rate limiting per API key) require
  Lua scripting or migration to Kong/Traefik.
