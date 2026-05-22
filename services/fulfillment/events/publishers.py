"""Outbound event publishers for fulfillment-service."""

from __future__ import annotations

import json

from aio_pika import ExchangeType, Message

from shared.events import OrderPackedEvent, OrderReturnInitiatedEvent


async def publish_order_packed(event: OrderPackedEvent, conn) -> None:
    """Publish order.packed after the order has been packed."""
    async with conn.channel() as channel:
        exchange = await channel.declare_exchange(
            "events", ExchangeType.TOPIC, durable=True
        )
        payload = {
            "event_id": str(event.event_id),
            "occurred_at": event.occurred_at.isoformat(),
            "order_id": str(event.order_id),
            "fulfillment_id": str(event.fulfillment_id),
        }
        await exchange.publish(
            Message(
                json.dumps(payload).encode(), content_type="application/json"
            ),
            routing_key="order.packed",
        )


async def publish_order_return_initiated(
    event: OrderReturnInitiatedEvent,
    conn,
) -> None:
    """Publish order.return_initiated when a return is triggered."""
    async with conn.channel() as channel:
        exchange = await channel.declare_exchange(
            "events", ExchangeType.TOPIC, durable=True
        )
        payload = {
            "event_id": str(event.event_id),
            "occurred_at": event.occurred_at.isoformat(),
            "order_id": str(event.order_id),
            "shipment_id": str(event.shipment_id),
        }
        await exchange.publish(
            Message(
                json.dumps(payload).encode(), content_type="application/json"
            ),
            routing_key="order.return_initiated",
        )
