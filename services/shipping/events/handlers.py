"""Inbound event handlers for shipping-service."""


async def handle_order_packed(event: dict) -> None:
    """Dispatch a shipment once the order has been packed."""
    raise NotImplementedError
