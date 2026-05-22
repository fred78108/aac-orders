# aac-orders

*This is an exercise with taking an architecture as code approach to vibe coding. This is solely AI created (claude) with human interaction focused as the "architect" in the project.*

**NOT INTENDED FOR PRODUCTION USE**: This is an experiment on patterns of development. I'm sharing this publicly to support communication (blog posts, hallway conversations, etc).


Event-driven order fulfillment platform — Python microservices on Docker Compose.

## Architecture

See [docs/architecture/](docs/architecture/README.md) for diagrams and design decisions.

Quick overview of the bounded contexts:

| Service | Responsibility |
|---|---|
| `order-service` | Accepts orders, orchestrates the saga entry point |
| `payment-service` | Charges, refunds, fraud checks via external gateway |
| `inventory-service` | Stock levels, reservations, pick-pack allocation |
| `fulfillment-service` | Warehouse operations, packing, dispatch readiness |
| `shipping-service` | Carrier integration, label generation, tracking |
| `notification-service` | Email / SMS triggered by domain events |

All services communicate asynchronously through **RabbitMQ**. The only synchronous path is the thin HTTP layer between the API gateway and `order-service`.

## Getting started

```bash
# 1. Install docs / diagram dependencies
pip install -e ".[docs]"

# 2. Ensure Graphviz is installed (required by `diagrams`)
#    macOS:  brew install graphviz
#    Ubuntu: apt-get install graphviz

# 3. Generate architecture diagrams
cd docs/architecture
python diagrams/generate_all.py
```

Generated PNGs land in `docs/architecture/generated/`.

## Development setup

```bash
pip install -e ".[dev]"
pytest
```
