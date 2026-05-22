"""Outbound event publishers for shipping-service."""
from shared.events import ShipmentDispatchedEvent, ShipmentFailedEvent


async def publish_shipment_dispatched(event: ShipmentDispatchedEvent) -> None:
    """Publish shipment.dispatched after a carrier accepts the shipment."""
    raise NotImplementedError


async def publish_shipment_failed(event: ShipmentFailedEvent) -> None:
    """Publish shipment.failed when a carrier reports a delivery failure."""
    raise NotImplementedError
