"""Inbound event handlers for inventory-service."""

from __future__ import annotations

from uuid import UUID

from inventory.db.repository import StockRepository
from inventory.domain.models import StockItem, StockReservation
from inventory.events.publishers import publish_stock_reserved
from shared.events import StockReservedEvent

_DEFAULT_SKU = "DEFAULT"


async def handle_payment_captured(
    event: dict, session_factory, amqp_conn
) -> None:
    """Reserve stock once payment has been captured."""
    order_id = UUID(event["order_id"])

    reservation = StockReservation(
        order_id=order_id,
        items=[StockItem(sku=_DEFAULT_SKU, quantity_available=1)],
    )

    repo = StockRepository(session_factory)
    await repo.reserve(reservation)

    await publish_stock_reserved(
        StockReservedEvent(
            order_id=order_id,
            reservation_id=reservation.id,
        ),
        amqp_conn,
    )
