# Architecture

Four diagrams model the system at different levels of abstraction,
following the [C4 model](https://c4model.com) approach.

## Generating the diagrams

```bash
# From the project root — install docs extras once
pip install -e ".[docs]"

# Graphviz must be available on PATH
# macOS:   brew install graphviz
# Ubuntu:  apt-get install graphviz

# Generate all PNGs
cd docs/architecture
python diagrams/generate_all.py
```

PNGs land in `docs/architecture/generated/`.

---

## Diagram index

### 1. System Context  (`diagrams/system_context.py`)
**Scope:** Who uses the platform and which external services it calls.

| Actor / System | Role |
|---|---|
| Customer | Places orders, tracks shipments via HTTPS |
| Payment Gateway (Stripe) | Authorises and captures charges |
| Shipping Carrier (FedEx/UPS) | Label generation and shipment tracking |
| Comms Provider (SendGrid/Twilio) | Email and SMS delivery |

---

### 2. Service Overview  (`diagrams/service_overview.py`)
**Scope:** All microservices, their databases, and shared infrastructure.

Each service owns its own PostgreSQL database (no shared schema).
The only synchronous call enters through the API gateway and reaches
`order-service`.  All other cross-service communication is async via
RabbitMQ.

| Service | Port | Database |
|---|---|---|
| API Gateway (Nginx) | 8080 | — |
| order-service | 8001 | orders_db |
| payment-service | 8002 | payments_db |
| inventory-service | 8003 | inventory_db |
| fulfillment-service | 8004 | fulfillment_db |
| shipping-service | 8005 | shipping_db |
| notification-service | 8006 | notifications_db |

Shared infrastructure: **RabbitMQ** (message broker), **Redis** (session
cache).

---

### 3. Event Flow  (`diagrams/event_flow.py`)
**Scope:** Choreography-based saga — happy path from order placement to
notification.

```
Customer
  │  POST /orders [HTTP]
  ▼
API Gateway ──► order-service
                    │ order.created ──────────────────────────────┐
                    ▼                                             │
              RabbitMQ                                     notification-
                    │ order.created                         service
                    ▼                                      (subscribes
              payment-service                              to all events)
                    │ payment.captured
                    ▼
              RabbitMQ
                    │ payment.captured
                    ▼
              inventory-service
                    │ stock.reserved
                    ▼
              RabbitMQ
                    │ stock.reserved
                    ▼
              fulfillment-service
                    │ order.packed
                    ▼
              RabbitMQ
                    │ order.packed
                    ▼
              shipping-service
                    │ shipment.dispatched
                    ▼
              RabbitMQ ──► notification-service
```

**Compensating events** (not shown in the happy-path diagram):

| Failure | Compensating event | Handler |
|---|---|---|
| `payment.failed` | — | order-service cancels order |
| `stock.insufficient` | `payment.refund_requested` | payment-service |
| `shipment.failed` | `order.return_initiated` | fulfillment-service |

---

### 4. Deployment  (`diagrams/deployment.py`)
**Scope:** Docker Compose containers and their network topology for local
development.

One Docker network (`aac-orders_default`) contains:

- **Ingress:** `nginx` (port 80)
- **Application:** 6 Python service containers (ports 8001–8006)
- **Messaging:** `rabbitmq` (AMQP :5672, management UI :15672)
- **Data:** 6 PostgreSQL containers (ports 5432–5437) + `redis` (:6379)

Each service container is stateless; all state lives in its paired
Postgres container and in RabbitMQ's durable queues.

---

## Key architectural decisions

| Decision | Choice | Rationale |
|---|---|---|
| Inter-service comms | Async events via RabbitMQ | Loose coupling; services can evolve independently |
| Data ownership | One DB per service | Enforces bounded contexts; no cross-schema joins |
| Saga pattern | Choreography (no orchestrator) | Simpler for linear happy-path; compensating events handle failures |
| Local runtime | Docker Compose | Minimal ops overhead; mirrors prod topology without Kubernetes |
| Language | Python 3.12 | Team familiarity; async support via `asyncio` |
