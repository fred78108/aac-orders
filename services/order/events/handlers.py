"""Inbound event handlers for order-service."""

from __future__ import annotations

from uuid import UUID

from order.db.repository import OrderRepository
from order.domain.models import OrderStatus


async def handle_payment_failed(event: dict, session_factory, amqp_conn) -> None:
    """Cancel the order when payment-service reports a failure."""
    order_id = UUID(event["order_id"])
    repo = OrderRepository(session_factory)
    await repo.update_status(order_id, OrderStatus.CANCELLED.value)
