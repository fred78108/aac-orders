"""Inbound event handlers for payment-service."""


async def handle_order_created(event: dict) -> None:
    """Charge the customer when a new order is created."""
    raise NotImplementedError


async def handle_stock_insufficient(event: dict) -> None:
    """Initiate a refund when inventory cannot fulfil the order."""
    raise NotImplementedError
