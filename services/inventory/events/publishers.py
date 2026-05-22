"""Outbound event publishers for inventory-service."""
from shared.events import StockInsufficientEvent, StockReservedEvent


async def publish_stock_reserved(event: StockReservedEvent) -> None:
    """Publish stock.reserved after successfully reserving inventory."""
    raise NotImplementedError


async def publish_stock_insufficient(event: StockInsufficientEvent) -> None:
    """Publish stock.insufficient when a SKU cannot be reserved."""
    raise NotImplementedError
