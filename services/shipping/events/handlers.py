"""Inbound event handlers for shipping-service."""

from __future__ import annotations

import uuid
from uuid import UUID

from shipping.db.repository import ShipmentRepository
from shipping.domain.models import Shipment
from shipping.events.publishers import publish_shipment_dispatched
from shared.events import ShipmentDispatchedEvent


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

    await publish_shipment_dispatched(
        ShipmentDispatchedEvent(
            order_id=order_id,
            shipment_id=shipment.id,
            tracking_number=tracking_number,
        ),
        amqp_conn,
    )
