"""Outbound event publishers for order-service."""
from __future__ import annotations

import json

from aio_pika import ExchangeType, Message

from shared.events import OrderCreatedEvent


async def publish_order_created(event: OrderCreatedEvent, conn) -> None:
    """Publish order.created — step 1 of the choreography saga."""
    async with conn.channel() as channel:
        exchange = await channel.declare_exchange(
            "events", ExchangeType.TOPIC, durable=True
        )
        payload = {
            "event_id": str(event.event_id),
            "occurred_at": event.occurred_at.isoformat(),
            "order_id": str(event.order_id),
            "customer_id": str(event.customer_id),
            "total_cents": event.total_cents,
        }
        await exchange.publish(
            Message(
                json.dumps(payload).encode(),
                content_type="application/json",
            ),
            routing_key="order.created",
        )
