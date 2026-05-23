"""Outbound event publishers for payment-service."""

from __future__ import annotations

import json

from aio_pika import ExchangeType, Message

from shared.events import PaymentCapturedEvent, PaymentFailedEvent, PaymentRefundRequestedEvent


async def publish_payment_captured(event: PaymentCapturedEvent, conn) -> None:
    """Publish payment.captured after a successful charge."""
    async with conn.channel() as channel:
        exchange = await channel.declare_exchange(
            "events", ExchangeType.TOPIC, durable=True
        )
        payload = {
            "event_id": str(event.event_id),
            "occurred_at": event.occurred_at.isoformat(),
            "order_id": str(event.order_id),
            "payment_id": str(event.payment_id),
            "amount_cents": event.amount_cents,
        }
        await exchange.publish(
            Message(
                json.dumps(payload).encode(), content_type="application/json"
            ),
            routing_key="payment.captured",
        )


async def publish_payment_failed(event: PaymentFailedEvent, conn) -> None:
    """Publish payment.failed when a charge is declined."""
    async with conn.channel() as channel:
        exchange = await channel.declare_exchange(
            "events", ExchangeType.TOPIC, durable=True
        )
        payload = {
            "event_id": str(event.event_id),
            "occurred_at": event.occurred_at.isoformat(),
            "order_id": str(event.order_id),
            "reason": event.reason,
        }
        await exchange.publish(
            Message(
                json.dumps(payload).encode(), content_type="application/json"
            ),
            routing_key="payment.failed",
        )


async def publish_payment_refund_requested(
    event: PaymentRefundRequestedEvent, conn
) -> None:
    """Publish payment.refund_requested to trigger a refund flow."""
    async with conn.channel() as channel:
        exchange = await channel.declare_exchange(
            "events", ExchangeType.TOPIC, durable=True
        )
        payload = {
            "event_id": str(event.event_id),
            "occurred_at": event.occurred_at.isoformat(),
            "order_id": str(event.order_id),
            "payment_id": str(event.payment_id),
            "amount_cents": event.amount_cents,
        }
        await exchange.publish(
            Message(
                json.dumps(payload).encode(), content_type="application/json"
            ),
            routing_key="payment.refund_requested",
        )
