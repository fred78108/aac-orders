"""Inbound event handlers for notification-service."""

from __future__ import annotations

from notification.db.repository import NotificationRepository
from notification.domain.models import (
    Notification,
    NotificationChannel,
    NotificationStatus,
)


async def handle_order_event(event: dict, session_factory, _amqp_conn) -> None:
    order_id = event.get("order_id", "unknown")
    customer_id = event.get("customer_id", order_id)
    notification = Notification(
        recipient=str(customer_id),
        channel=NotificationChannel.EMAIL,
        subject="Order received",
        body=f"Your order {order_id} has been received and is being processed.",
        status=NotificationStatus.SENT,
    )
    await NotificationRepository(session_factory).save(notification)


async def handle_payment_event(
    event: dict, session_factory, _amqp_conn
) -> None:
    order_id = event.get("order_id", "unknown")
    reason = event.get("reason")
    if reason:
        subject = "Payment failed"
        body = f"Payment for order {order_id} failed: {reason}."
    else:
        subject = "Payment confirmed"
        body = f"Payment for order {order_id} has been confirmed."
    notification = Notification(
        recipient=str(order_id),
        channel=NotificationChannel.EMAIL,
        subject=subject,
        body=body,
        status=NotificationStatus.SENT,
    )
    await NotificationRepository(session_factory).save(notification)


async def handle_stock_event(event: dict, session_factory, _amqp_conn) -> None:
    order_id = event.get("order_id", "unknown")
    sku = event.get("sku")
    if sku:
        subject = "Item out of stock"
        body = (
            f"Unfortunately, item {sku} for order {order_id} is out of stock."
        )
    else:
        subject = "Stock reserved"
        body = f"Stock has been reserved for order {order_id}."
    notification = Notification(
        recipient=str(order_id),
        channel=NotificationChannel.EMAIL,
        subject=subject,
        body=body,
        status=NotificationStatus.SENT,
    )
    await NotificationRepository(session_factory).save(notification)


async def handle_shipment_event(
    event: dict, session_factory, _amqp_conn
) -> None:
    order_id = event.get("order_id", "unknown")
    tracking_number = event.get("tracking_number")
    reason = event.get("reason")
    if tracking_number:
        subject = "Order shipped"
        body = f"Your order {order_id} has been shipped. Tracking: {tracking_number}."
    elif reason:
        subject = "Shipment failed"
        body = f"Shipment for order {order_id} failed: {reason}."
    else:
        subject = "Shipment update"
        body = f"There is an update on the shipment for order {order_id}."
    notification = Notification(
        recipient=str(order_id),
        channel=NotificationChannel.EMAIL,
        subject=subject,
        body=body,
        status=NotificationStatus.SENT,
    )
    await NotificationRepository(session_factory).save(notification)
