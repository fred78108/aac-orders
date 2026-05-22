"""Inbound event handlers for notification-service."""


async def handle_order_event(event: dict) -> None:
    """Send an external notification in response to an order.* event."""
    raise NotImplementedError


async def handle_payment_event(event: dict) -> None:
    """Send an external notification in response to a payment.* event."""
    raise NotImplementedError


async def handle_stock_event(event: dict) -> None:
    """Send an external notification in response to a stock.* event."""
    raise NotImplementedError


async def handle_shipment_event(event: dict) -> None:
    """Send an external notification in response to a shipment.* event."""
    raise NotImplementedError
