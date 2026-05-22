# ADR-0006: Docker Compose for local runtime

| Field    | Value      |
|----------|------------|
| Status   | Accepted   |
| Date     | 2026-05-22 |
| Deciders | Fred       |

## Context

The system comprises 15+ containers (6 services, 6 Postgres instances,
RabbitMQ, Redis, Nginx). A local runtime environment must start all of them
reproducibly, wire their networking, and mirror the production topology closely
enough that architecture decisions validated locally remain valid at scale.

## Considered Options

- **Docker Compose** — declarative `docker-compose.yml`; single command to
  start the full stack; no cluster required.
- **Kubernetes (minikube / kind)** — production-equivalent orchestration;
  significantly higher local-dev complexity and resource usage.
- **Bare Docker (shell scripts)** — full control; brittle; networking and
  dependency ordering managed manually.
- **Podman Compose** — Docker Compose-compatible; drop-in for Docker but less
  ecosystem tooling.

## Decision Outcome

Chose **Docker Compose**.

A single `docker compose up` starts the entire 15-container topology, including
health-check-based dependency ordering (services wait for Postgres and RabbitMQ
to be ready). The `docker-compose.yml` file is the authoritative, version-controlled
description of the runtime environment — it *is* the infrastructure definition for
local development, in line with the architecture-as-code goal.

Kubernetes is the right choice for production orchestration but introduces
networking abstractions (Services, Ingress, ConfigMaps) that would obscure
the domain architecture in a demonstration context. The topology difference is
documented rather than hidden.

## Consequences

**Positive**
- One file (`docker-compose.yml`) fully describes the local environment;
  new contributors run `docker compose up` with no additional setup.
- Named Docker network (`aac-orders_default`) makes inter-container DNS
  resolution automatic and predictable.
- Each service container is stateless; state lives in paired Postgres containers
  and RabbitMQ durable queues — portable to Kubernetes with minimal changes.

**Negative / watch-outs**
- 15+ containers place meaningful RAM demand on a developer laptop (~4–6 GB).
- Docker Compose does not provide pod-level resource limits, rolling updates, or
  health-driven rescheduling — production deployment would use Kubernetes or ECS.
- `docker-compose.yml` must be kept in sync with any future Helm charts or
  Terraform modules that describe the production environment.
