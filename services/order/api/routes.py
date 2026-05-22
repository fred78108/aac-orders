from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel

from order.db.repository import OrderRepository
from order.domain.models import Order, OrderItem
from order.events.publishers import publish_order_created
from shared.events import OrderCreatedEvent

router = APIRouter()


class OrderItemRequest(BaseModel):
    sku: str
    quantity: int
    unit_price_cents: int


class PlaceOrderRequest(BaseModel):
    customer_id: UUID
    items: list[OrderItemRequest]


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "order-service"}


@router.post("/orders", status_code=202)
async def place_order(body: PlaceOrderRequest, request: Request) -> dict:
    """Receive POST /orders, validate, persist, and publish order.created."""
    order = Order(
        customer_id=body.customer_id,
        items=[
            OrderItem(
                sku=i.sku,
                quantity=i.quantity,
                unit_price_cents=i.unit_price_cents,
            )
            for i in body.items
        ],
    )

    repo = OrderRepository(request.app.state.session_factory)
    await repo.save(order)

    event = OrderCreatedEvent(
        order_id=order.id,
        customer_id=order.customer_id,
        total_cents=order.total_cents,
    )
    await publish_order_created(event, request.app.state.amqp_conn)

    return {"order_id": str(order.id), "status": order.status.value}
