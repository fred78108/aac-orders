"""Inbound event handlers for payment-service."""

from __future__ import annotations

from uuid import UUID

from payment.db.repository import PaymentRepository
from payment.domain.models import Payment, PaymentStatus
from payment.events.publishers import (
    publish_payment_captured,
    publish_payment_refund_requested,
)
from shared.events import PaymentCapturedEvent, PaymentRefundRequestedEvent


async def handle_order_created(
    event: dict, session_factory, amqp_conn
) -> None:
    """Charge the customer when a new order is created."""
    order_id = UUID(event["order_id"])
    customer_id = UUID(event["customer_id"])
    total_cents = int(event["total_cents"])

    payment = Payment(
        order_id=order_id,
        customer_id=customer_id,
        amount_cents=total_cents,
    )

    repo = PaymentRepository(session_factory)
    await repo.save(payment)

    # Simulate payment gateway capture — always succeeds in this implementation
    payment.status = PaymentStatus.CAPTURED
    await repo.update_status(payment.id, payment.status.value)

    await publish_payment_captured(
        PaymentCapturedEvent(
            order_id=order_id,
            payment_id=payment.id,
            amount_cents=total_cents,
        ),
        amqp_conn,
    )


async def handle_stock_insufficient(
    event: dict, session_factory, amqp_conn
) -> None:
    """Initiate a refund when inventory cannot fulfil the order."""
    order_id = UUID(event["order_id"])

    repo = PaymentRepository(session_factory)
    payment = await repo.get_by_order_id(order_id)

    await repo.update_status(payment.id, PaymentStatus.REFUNDED.value)

    await publish_payment_refund_requested(
        PaymentRefundRequestedEvent(
            order_id=order_id,
            payment_id=payment.id,
            amount_cents=payment.amount_cents,
        ),
        amqp_conn,
    )
