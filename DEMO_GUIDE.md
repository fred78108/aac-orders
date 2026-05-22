# aac-orders Demo Guide

A step-by-step walkthrough for demonstrating the event-driven order fulfillment platform to an audience.

---

## What this is

**aac-orders** is a six-service order fulfillment backend that uses a **choreography saga** over RabbitMQ. There is no orchestrator — each service reacts to events and publishes its own. The only synchronous surface is one HTTP endpoint: `POST /orders`.

The codebase ships with architecture tests, domain models, and event schemas fully defined. The service handlers and publishers are stubs (they raise `NotImplementedError`), which means the full event chain is not yet wired end-to-end. This demo covers:

1. Starting the stack and verifying infrastructure
2. Placing an order and observing the HTTP layer
3. Touring the RabbitMQ topology
4. Walking the happy-path and failure flows as designed
5. Showing the architecture test suite

---

## Web interface (recommended for live demos)

A browser-based dashboard is included at `demo/`. It starts automatically with `docker compose up --build` and is available at **http://localhost:9000**.

The dashboard provides:

| Panel | What it shows |
|---|---|
| **Service Health** | Live status for all six services, auto-refreshed every 5 s |
| **Choreography Saga flow** | Annotated event-chain diagram (happy path + three failure scenarios) |
| **Place Order** | Form with four preset scenarios, computed total, and a "copy as curl" toggle |
| **RabbitMQ Monitor** | Per-queue message depth and consumer count, auto-refreshed every 3 s |
| **Exchange bindings** | Topic routing reference table |
| **Port map** | All service and infrastructure ports at a glance |

No separate installation is needed — the dashboard is built and started as part of the normal `docker compose up --build`. It can also be run standalone on the host (without Docker) if the rest of the stack is running:

```bash
cd demo
pip install -r requirements.txt
python app.py          # opens on http://localhost:9000
```

See [ADR-0012](docs/architecture/decisions/0012-flask-demo-dashboard.md) for the technology choices behind the dashboard.

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Docker Desktop | 4.x+ | Docker Compose v2 is bundled |
| `curl` or `httpie` | any | for HTTP calls |
| `psql` | any | optional, for DB inspection |
| Graphviz | any | optional, for generating diagrams |

```bash
# verify docker compose is available
docker compose version
```

---

## 1. Start the stack

```bash
cd /path/to/aac-orders
docker compose up --build
```

Wait until you see all six services log `Application startup complete`. The startup order is:

1. **PostgreSQL** × 6 (one per service, ports 5432–5437)
2. **RabbitMQ** (AMQP :5672, Management UI :15672)
3. **Redis** (:6379)
4. **Six application services** (:8001–:8006)
5. **Nginx** API gateway (:8080)

---

## 2. Verify health

Each service exposes `GET /health`. Nginx proxies `/health` to `order-service`.

```bash
# via the API gateway (preferred entry point)
curl http://localhost:8080/health
# {"status": "ok", "service": "order-service"}

# individual services
curl http://localhost:8001/health   # order-service
curl http://localhost:8002/health   # payment-service
curl http://localhost:8003/health   # inventory-service
curl http://localhost:8004/health   # fulfillment-service
curl http://localhost:8005/health   # shipping-service
curl http://localhost:8006/health   # notification-service
```

Open the **RabbitMQ Management UI** at http://localhost:15672 (login: `guest` / `guest`). You should see:

- **Connections** tab: six consumer connections (one per service)
- **Queues** tab: six queues, each with at least one consumer
- **Exchanges** tab: the exchange bindings that define which service receives which event

---

## 3. Service and port map

| Service | HTTP port | Database | DB port |
|---|---|---|---|
| order-service | :8001 | orders_db | :5432 |
| payment-service | :8002 | payments_db | :5433 |
| inventory-service | :8003 | inventory_db | :5434 |
| fulfillment-service | :8004 | fulfillment_db | :5435 |
| shipping-service | :8005 | shipping_db | :5436 |
| notification-service | :8006 | notifications_db | :5437 |

Nginx (:8080) routes only `/orders` and `/health` to `order-service`. No other service is reachable from outside the Docker network by design.

---

## 4. Place an order (happy path)

`POST /orders` is the sole entry point for the entire system.

```bash
curl -s -X POST http://localhost:8080/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "11111111-1111-1111-1111-111111111111",
    "items": [
      {
        "sku": "WIDGET-42",
        "quantity": 2,
        "unit_price_cents": 2500
      }
    ]
  }' | python3 -m json.tool
```

Expected response: **HTTP 202 Accepted**

The order service validates the request, persists the order with status `PENDING`, and publishes an `order.created` event to RabbitMQ. The HTTP call returns immediately — all downstream processing is asynchronous.

### Order item fields

| Field | Type | Description |
|---|---|---|
| `customer_id` | UUID | Identifies the customer |
| `sku` | string | Stock keeping unit identifier |
| `quantity` | int | Number of units |
| `unit_price_cents` | int | Unit price in cents (e.g. `2500` = $25.00) |

The `total_cents` is computed by the service: `sum(quantity × unit_price_cents)`.

---

## 5. The happy-path event chain

Once `order.created` is published, the saga proceeds through five events with no HTTP calls between services:

```
POST /orders (HTTP)
    ↓
order-service          → publishes  order.created
    ↓
payment-service        → publishes  payment.captured
    ↓
inventory-service      → publishes  stock.reserved
    ↓
fulfillment-service    → publishes  order.packed
    ↓
shipping-service       → publishes  shipment.dispatched
```

`notification-service` subscribes to **all** events (`order.*`, `payment.*`, `stock.*`, `shipment.*`) and fires an email or SMS at each milestone.

### Event schemas (from `services/shared/events.py`)

All events share a base envelope:

| Field | Type | Description |
|---|---|---|
| `event_id` | UUID | Unique, auto-generated |
| `occurred_at` | datetime | UTC timestamp, auto-generated |

Event-specific payloads:

| Event | Key fields |
|---|---|
| `order.created` | `order_id`, `customer_id`, `total_cents` |
| `payment.captured` | `order_id`, `payment_id`, `amount_cents` |
| `stock.reserved` | `order_id`, `reservation_id` |
| `order.packed` | `order_id`, `fulfillment_id` |
| `shipment.dispatched` | `order_id`, `shipment_id`, `tracking_number` |

### Order status progression

As each event is processed, `order-service` updates the order record:

```
PENDING → PAYMENT_PROCESSING → PAID → PACKED → DISPATCHED
```

Inspect the final state:

```bash
psql -h localhost -p 5432 -U postgres -d orders_db \
  -c "SELECT id, status, total_cents FROM orders ORDER BY created_at DESC LIMIT 5;"
```

---

## 6. Observing events in RabbitMQ

Open http://localhost:15672 and watch during a `POST /orders` call.

### Exchanges tab

The main exchange uses **topic routing**. Each queue is bound to specific routing keys:

| Queue | Bound routing keys |
|---|---|
| `order-service_queue` | `payment.failed` |
| `payment-service_queue` | `order.created`, `stock.insufficient` |
| `inventory-service_queue` | `payment.captured` |
| `fulfillment-service_queue` | `stock.reserved`, `shipment.failed` |
| `shipping-service_queue` | `order.packed` |
| `notification-service_queue` | `order.*`, `payment.*`, `stock.*`, `shipment.*` |

### Queues tab — what to watch

- **Message rates**: each event appears briefly in the queue and is consumed within milliseconds in the happy path
- **Ready / Unacked counts**: in failure scenarios, unhandled messages stay in the queue (visible as `Ready > 0`)
- Click any queue → **Get messages** to inspect the raw JSON payload of any pending message

---

## 7. Failure flows and compensation

The saga handles three failure scenarios without a central coordinator. Each service is responsible for publishing its own compensating event.

### Scenario A — Payment fails

```
payment-service receives order.created
    → external gateway rejects charge
    → publishes payment.failed { order_id, reason }
        ↓
order-service handles payment.failed
    → updates order status: PENDING → CANCELLED
    → saga terminates (no further events)
```

**What to observe:**
- `payment.failed` appears in `order-service_queue`
- Order record in `orders_db`: status = `CANCELLED`
- No events in any other queue

### Scenario B — Insufficient stock

```
inventory-service receives payment.captured
    → stock check fails for the requested SKU
    → publishes stock.insufficient { order_id, sku }
        ↓
payment-service handles stock.insufficient
    → publishes payment.refund_requested { order_id, payment_id, amount_cents }
        ↓
notification-service receives stock.insufficient
    → sends "out of stock" notification
```

**What to observe:**
- `stock.insufficient` routes to both `payment-service_queue` and `notification-service_queue`
- `payment.refund_requested` published by payment-service
- Payment record in `payments_db`: status moves toward `REFUNDED`

### Scenario C — Shipment fails

```
shipping-service receives order.packed
    → carrier API fails
    → publishes shipment.failed { order_id, shipment_id, reason }
        ↓
fulfillment-service handles shipment.failed
    → publishes order.return_initiated { order_id, shipment_id }
        ↓
notification-service receives shipment.failed
    → sends "shipping failed" notification
```

**What to observe:**
- `shipment.failed` routes to both `fulfillment-service_queue` and `notification-service_queue`
- `order.return_initiated` published — this would trigger warehouse intake in a complete implementation
- Fulfillment record in `fulfillment_db`: status = `RETURNED`

---

## 8. Inspect service databases

Each service owns its database exclusively — no cross-service joins exist anywhere in the codebase.

```bash
# Order lifecycle
psql -h localhost -p 5432 -U postgres -d orders_db \
  -c "SELECT id, customer_id, status, total_cents FROM orders;"

# Payment status
psql -h localhost -p 5433 -U postgres -d payments_db \
  -c "SELECT id, order_id, status, amount_cents FROM payments;"

# Stock reservations
psql -h localhost -p 5434 -U postgres -d inventory_db \
  -c "SELECT id, order_id FROM stock_reservations;"

# Fulfillment packing status
psql -h localhost -p 5435 -U postgres -d fulfillment_db \
  -c "SELECT id, order_id, status FROM fulfillment_orders;"

# Shipments with tracking
psql -h localhost -p 5436 -U postgres -d shipping_db \
  -c "SELECT id, order_id, status, tracking_number FROM shipments;"

# Notification history
psql -h localhost -p 5437 -U postgres -d notifications_db \
  -c "SELECT id, recipient, channel, subject, status FROM notifications;"
```

---

## 9. Architecture diagrams

Generate PNGs from the diagram-as-code files:

```bash
pip install -e ".[docs]"
brew install graphviz          # macOS; or: apt-get install graphviz

cd docs/architecture
python diagrams/generate_all.py
```

Output lands in `docs/architecture/generated/`:

| File | Shows |
|---|---|
| `service_overview.png` | All six services and their responsibilities |
| `deployment.png` | Docker Compose topology, ports, databases |
| `event_flow.png` | Full happy-path event chain with compensating flows |

The `event_flow` diagram is the most useful for audience explanation — it shows the complete saga visually, including compensation arrows.

---

## 10. Architecture tests

The test suite validates the architectural contracts without running containers:

```bash
pip install -e ".[dev]"
pytest -v
```

Key test files:

| Test | What it checks |
|---|---|
| `tests/test_event_saga.py` | Happy-path event order, compensating events, no-orchestrator invariant |
| `tests/test_deployment_topology.py` | Port uniqueness, DB pairing, network config |
| `tests/services/test_order_service.py` | Order service is saga entry point, handles payment.failed |
| `tests/services/test_payment_service.py` | Handles order.created and stock.insufficient, publishes payment.captured and payment.refund_requested |
| `tests/services/test_inventory_service.py` | Handles payment.captured, publishes stock.reserved and stock.insufficient |
| `tests/services/test_fulfillment_service.py` | Handles stock.reserved and shipment.failed, publishes order.packed and order.return_initiated |
| `tests/services/test_shipping_service.py` | Handles order.packed, publishes shipment.dispatched and shipment.failed |
| `tests/services/test_notification_service.py` | Subscribes to all four event namespaces |

These tests describe the **intended behavior** of each service. Running them before implementing handlers gives you a red/green baseline for TDD.

---

## 11. Suggested demo script

### Option A — Web dashboard (recommended, no terminal required for audience)

1. **`docker compose up --build`** — narrate the six services starting independently
2. **Open http://localhost:9000** — show the dashboard; point out the saga flow diagram and explain choreography vs. orchestration using the visual
3. **Service Health strip** — six green dots confirm the stack is up; cross-reference with `:8001–:8006`
4. **RabbitMQ Monitor panel** — show queue depths at zero and consumer count at 1 per queue
5. **Click "Standard Order" preset → POST /orders** — show the HTTP response (202 or 500/TDD baseline); explain what would happen end-to-end once handlers are implemented
6. **Click "Payment Fail" preset** — walk through Scenario A using the compensation flow diagram on the same page
7. **Switch to terminal → `pytest -v`** — show architecture tests green, service tests red
8. **Open one handler stub** — show the TDD starting point

### Option B — Terminal-first (curl + RabbitMQ UI)

1. **Open the architecture diagram** (`event_flow.png`) — explain choreography vs. orchestration
2. **`docker compose up --build`** — point out the six services starting independently
3. **Open RabbitMQ Management UI** — show the queues and exchange bindings; explain topic routing
4. **`curl POST /orders`** — place a happy-path order; show 202 Accepted
5. **Refresh RabbitMQ Queues tab** — trace the event pulse through each queue
6. **Query `orders_db`** — show the status field advancing from PENDING to DISPATCHED
7. **Place an order that triggers payment failure** — show the saga stopping early at CANCELLED
8. **Run `pytest -v`** — show architecture tests green, service tests red (stubs not implemented)
9. **Open one handler stub** — show the TDD starting point

---

## 12. Tear down

```bash
# stop and remove containers, networks, volumes
docker compose down -v
```

The `-v` flag removes the named volumes (PostgreSQL data). Omit it if you want to preserve data between demo runs.
