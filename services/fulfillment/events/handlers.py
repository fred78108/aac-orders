"""Inbound event handlers for fulfillment-service."""


async def handle_stock_reserved(event: dict) -> None:
    """Begin packing an order once stock has been reserved."""
    raise NotImplementedError


async def handle_shipment_failed(event: dict) -> None:
    """Initiate a return when the shipping carrier reports a failure."""
    raise NotImplementedError
