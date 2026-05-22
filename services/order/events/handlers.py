"""Inbound event handlers for order-service."""


async def handle_payment_failed(event: dict) -> None:
    """Cancel the order when payment-service reports a failure."""
    raise NotImplementedError
