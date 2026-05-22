# ADR-0002: RabbitMQ as message broker

| Field    | Value      |
|----------|------------|
| Status   | Accepted   |
| Date     | 2026-05-22 |
| Deciders | Fred       |

## Context

The choreography saga requires a durable, async message transport between
services. The broker must support pub/sub fan-out (notification-service subscribes
to all events) as well as point-to-point queuing for compensating events.

## Considered Options

- **RabbitMQ** — mature AMQP broker; exchange/queue model; management UI; official
  Docker image.
- **Apache Kafka** — distributed commit log; strong ordering and replay guarantees;
  heavier operational footprint.
- **Redis Streams** — lightweight streams on an already-present Redis instance.
- **AWS SQS/SNS** — managed; eliminates broker ops, but introduces a cloud
  dependency that conflicts with the fully-local Docker Compose goal.

## Decision Outcome

Chose **RabbitMQ**.

AMQP exchanges give direct support for both fan-out (topic exchange, all
services binding to `order.*`) and selective routing (direct exchange for
compensating commands). Durable queues and publisher confirms satisfy
at-least-once delivery without additional infrastructure.

Kafka's replay and partitioning strengths are not needed at this scale and add
significant local-dev complexity (Zookeeper or KRaft, topic partitioning, offset
management). Redis Streams would work but conflates caching and messaging
responsibilities in a single dependency.

## Consequences

**Positive**
- Single AMQP dependency covers all messaging patterns used in the saga.
- Management UI (`:15672`) gives real-time visibility into queues and bindings.
- Official `rabbitmq:3-management` Docker image requires zero extra configuration
  for local dev.

**Negative / watch-outs**
- RabbitMQ does not retain messages after they are acknowledged; event replay
  (e.g., rebuilding a read model) requires a separate event store or log.
- At-least-once delivery means consumers must be idempotent.

## Related decisions

- [ADR-0001](0001-choreography-saga-pattern.md) — saga coordination model that
  drives the messaging requirements
