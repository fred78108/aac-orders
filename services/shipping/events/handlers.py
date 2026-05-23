"""Inbound event handlers for shipping-service."""

from __future__ import annotations

import uuid
from uuid import UUID

from shipping.db.repository import ShipmentRepository
from shipping.domain.models import Shipment
from shipping.domain.models import ShipmentStatus
from shipping.events.publishers import publish_shipment_dispatched, publish_shipment_failed
from shared.events import ShipmentDispatchedEvent, ShipmentFailedEvent


async def handle_order_packed(event: dict, session_factory, amqp_conn) -> None:
    """Dispatch a shipment once the order has been packed."""
    order_id = UUID(event["order_id"])
    tracking_number = uuid.uuid4().hex[:12].upper()

    shipment = Shipment(
        order_id=order_id,
        carrier="DHL",
        tracking_number=tracking_number,
    )

    repo = ShipmentRepository(session_factory)
    await repo.save(shipment)

    # Simulate carrier rejection: tracking numbers ending in "0" (~6% rate)
    if tracking_number.endswith("0"):
        shipment.status = ShipmentStatus.FAILED
        await repo.update_status(shipment.id, shipment.status.value)
        await publish_shipment_failed(
            ShipmentFailedEvent(
                order_id=order_id,
                shipment_id=shipment.id,
                reason="carrier rejected shipment",
            ),
            amqp_conn,
        )
        return

    await publish_shipment_dispatched(
        ShipmentDispatchedEvent(
            order_id=order_id,
            shipment_id=shipment.id,
            tracking_number=tracking_number,
        ),
        amqp_conn,
    )
