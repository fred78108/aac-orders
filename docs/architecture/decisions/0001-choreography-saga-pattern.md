# ADR-0001: Choreography-based saga pattern

| Field    | Value      |
|----------|------------|
| Status   | Accepted   |
| Date     | 2026-05-22 |
| Deciders | Fred       |

## Context

Order fulfillment is a multi-step business process spanning six services:
order → payment → inventory → fulfillment → shipping → notification.
The process must handle partial failures with compensating transactions
(e.g., refund payment when stock is insufficient).

Two established patterns exist for distributed saga coordination.

## Considered Options

- **Choreography** — each service reacts to events published by the previous
  step; no central coordinator exists.
- **Orchestration** — a dedicated saga orchestrator service issues commands to
  each participant and tracks overall state.

## Decision Outcome

Chose **choreography**.

The happy path is linear and well-defined (order → payment → inventory →
fulfillment → shipping). Choreography handles this naturally with no added
infrastructure. Each service remains loosely coupled: it only needs to know
which events to consume and which to publish, not the shape of the overall saga.

Compensating events (`payment.refund_requested`, `order.return_initiated`) are
emitted by the failing service and consumed by the appropriate upstream service,
keeping rollback logic co-located with domain logic.

## Consequences

**Positive**
- No orchestrator service to build, deploy, or scale.
- Services are independently deployable with no shared coordinator dependency.
- Adding a new step (e.g., fraud-check service) requires only publishing/consuming
  the right events.

**Negative / watch-outs**
- End-to-end saga state is implicit in the event stream; there is no single place
  to query "what step is order 123 currently on?" — observability tooling must
  correlate events by `order_id`.
- Cyclic or complex failure paths (e.g., partial shipment) are harder to reason
  about than in an orchestrated saga where the orchestrator owns the state machine.

## Related decisions

- [ADR-0002](0002-rabbitmq-as-message-broker.md) — event transport
