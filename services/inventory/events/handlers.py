"""Inbound event handlers for inventory-service."""


async def handle_payment_captured(event: dict) -> None:
    """Reserve stock once payment has been captured."""
    raise NotImplementedError
