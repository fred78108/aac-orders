"""Outbound event publishers for inventory-service."""

from __future__ import annotations

import json

from aio_pika import ExchangeType, Message

from shared.events import StockInsufficientEvent, StockReservedEvent


async def publish_stock_reserved(event: StockReservedEvent, conn) -> None:
    """Publish stock.reserved after successfully reserving inventory."""
    async with conn.channel() as channel:
        exchange = await channel.declare_exchange(
            "events", ExchangeType.TOPIC, durable=True
        )
        payload = {
            "event_id": str(event.event_id),
            "occurred_at": event.occurred_at.isoformat(),
            "order_id": str(event.order_id),
            "reservation_id": str(event.reservation_id),
        }
        await exchange.publish(
            Message(
                json.dumps(payload).encode(), content_type="application/json"
            ),
            routing_key="stock.reserved",
        )


async def publish_stock_insufficient(
    event: StockInsufficientEvent, conn
) -> None:
    """Publish stock.insufficient when a SKU cannot be reserved."""
    async with conn.channel() as channel:
        exchange = await channel.declare_exchange(
            "events", ExchangeType.TOPIC, durable=True
        )
        payload = {
            "event_id": str(event.event_id),
            "occurred_at": event.occurred_at.isoformat(),
            "order_id": str(event.order_id),
            "sku": event.sku,
        }
        await exchange.publish(
            Message(
                json.dumps(payload).encode(), content_type="application/json"
            ),
            routing_key="stock.insufficient",
        )
