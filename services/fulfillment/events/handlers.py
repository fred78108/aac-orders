"""Inbound event handlers for fulfillment-service."""

from __future__ import annotations

from uuid import UUID

from fulfillment.db.repository import FulfillmentRepository
from fulfillment.domain.models import FulfillmentOrder, PackingStatus
from fulfillment.events.publishers import (
    publish_order_packed,
    publish_order_return_initiated,
)
from shared.events import OrderPackedEvent, OrderReturnInitiatedEvent


async def handle_stock_reserved(
    event: dict, session_factory, amqp_conn
) -> None:
    """Begin packing an order once stock has been reserved."""
    order_id = UUID(event["order_id"])

    fulfillment_order = FulfillmentOrder(order_id=order_id, items=[])

    repo = FulfillmentRepository(session_factory)
    await repo.save(fulfillment_order)

    await publish_order_packed(
        OrderPackedEvent(
            order_id=order_id,
            fulfillment_id=fulfillment_order.id,
        ),
        amqp_conn,
    )


async def handle_shipment_failed(
    event: dict, session_factory, amqp_conn
) -> None:
    """Initiate a return when the shipping carrier reports a failure."""
    order_id = UUID(event["order_id"])
    shipment_id = UUID(event["shipment_id"])

    repo = FulfillmentRepository(session_factory)
    fulfillment_order = await repo.get_by_order_id(order_id)
    await repo.update_status(
        fulfillment_order.id, PackingStatus.RETURNED.value
    )

    await publish_order_return_initiated(
        OrderReturnInitiatedEvent(
            order_id=order_id,
            shipment_id=shipment_id,
        ),
        amqp_conn,
    )
