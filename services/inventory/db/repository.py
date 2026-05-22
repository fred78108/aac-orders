from __future__ import annotations

from uuid import UUID

from inventory.domain.models import StockItem, StockReservation


class StockRepository:
    async def get_item(self, sku: str) -> StockItem:
        raise NotImplementedError

    async def reserve(self, reservation: StockReservation) -> None:
        raise NotImplementedError

    async def release(self, reservation_id: UUID) -> None:
        raise NotImplementedError
