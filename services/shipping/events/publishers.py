"""Outbound event publishers for shipping-service."""

from __future__ import annotations

import json

from aio_pika import ExchangeType, Message

from shared.events import ShipmentDispatchedEvent, ShipmentFailedEvent


async def publish_shipment_dispatched(
    event: ShipmentDispatchedEvent, conn
) -> None:
    """Publish shipment.dispatched after a carrier accepts the shipment."""
    async with conn.channel() as channel:
        exchange = await channel.declare_exchange(
            "events", ExchangeType.TOPIC, durable=True
        )
        payload = {
            "event_id": str(event.event_id),
            "occurred_at": event.occurred_at.isoformat(),
            "order_id": str(event.order_id),
            "shipment_id": str(event.shipment_id),
            "tracking_number": event.tracking_number,
        }
        await exchange.publish(
            Message(
                json.dumps(payload).encode(), content_type="application/json"
            ),
            routing_key="shipment.dispatched",
        )


async def publish_shipment_failed(event: ShipmentFailedEvent, conn) -> None:
    """Publish shipment.failed when a carrier reports a delivery failure."""
    async with conn.channel() as channel:
        exchange = await channel.declare_exchange(
            "events", ExchangeType.TOPIC, durable=True
        )
        payload = {
            "event_id": str(event.event_id),
            "occurred_at": event.occurred_at.isoformat(),
            "order_id": str(event.order_id),
            "shipment_id": str(event.shipment_id),
            "reason": event.reason,
        }
        await exchange.publish(
            Message(
                json.dumps(payload).encode(), content_type="application/json"
            ),
            routing_key="shipment.failed",
        )
