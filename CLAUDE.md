# aac-orders

Event-driven order fulfillment platform — 6 Python microservices, RabbitMQ choreography saga, Docker Compose.

## Architecture quick-reference

| Service | Port | Database | Publishes | Subscribes |
|---|---|---|---|---|
| order | 8001 | orders_db :5432 | order.created | payment.failed |
| payment | 8002 | payments_db :5433 | payment.captured, payment.refund_requested | order.created, stock.insufficient |
| inventory | 8003 | inventory_db :5434 | stock.reserved, stock.insufficient | payment.captured |
| fulfillment | 8004 | fulfillment_db :5435 | order.packed, order.return_initiated | stock.reserved, shipment.failed |
| shipping | 8005 | shipping_db :5436 | shipment.dispatched, shipment.failed | order.packed |
| notification | 8006 | notifications_db :5437 | — | order.*, payment.*, stock.*, shipment.* |

Shared infrastructure: RabbitMQ :5672/:15672, Redis :6379, Nginx :8080→:80.

## Repository layout

```
services/
  shared/           # shared library — importable as `shared` in all contexts
  order/            # saga entry point (only service with HTTP POST)
  payment/
  inventory/
  fulfillment/
  shipping/
  notification/
docker-compose.yml
nginx/nginx.conf
docs/architecture/  # ADRs, diagrams-as-code, generated PNGs
tests/              # pytest suite — architecture + service tests
```

## Internal service layout (every service follows this pattern)

```
services/<name>/
  __init__.py
  app.py            # FastAPI app factory: create_app() -> FastAPI
  main.py           # uvicorn entry point
  settings.py       # pydantic-settings Settings class; reads env vars
  api/
    __init__.py
    routes.py       # HTTP routes (health for all; POST /orders for order only)
  domain/
    __init__.py
    models.py       # domain dataclasses/enums — no I/O
  events/
    __init__.py
    handlers.py     # async functions that handle inbound events
    publishers.py   # async functions that publish outbound events
  db/
    __init__.py
    repository.py   # repository class stub
  Dockerfile
  requirements.txt
```

## Import conventions

- Within a service: absolute imports — `from order.domain.models import Order`
- Shared library: `from shared.events import OrderCreatedEvent`
- Docker build context is the project root; each Dockerfile copies `services/shared` and `services/<name>`

## Running locally

```bash
# Build and start everything
docker compose up --build

# Run tests (no containers needed)
pip install -e ".[dev]"
pytest
```

## TDD workflow

1. Add a failing test to `tests/services/test_<name>_service.py`
2. Write the minimum implementation in `services/<name>/`
3. `pytest tests/services/test_<name>_service.py`
