"""Outbound event publishers for fulfillment-service."""
from shared.events import OrderPackedEvent, OrderReturnInitiatedEvent


async def publish_order_packed(event: OrderPackedEvent) -> None:
    """Publish order.packed after the order has been packed."""
    raise NotImplementedError


async def publish_order_return_initiated(event: OrderReturnInitiatedEvent) -> None:
    """Publish order.return_initiated when a return is triggered."""
    raise NotImplementedError
