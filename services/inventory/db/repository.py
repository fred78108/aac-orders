from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from inventory.db.models import InventoryItemRow, ReservationRow
from inventory.domain.models import StockItem, StockReservation


class StockRepository:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        self._sf = session_factory

    async def get_item(self, sku: str) -> StockItem:
        async with self._sf() as session:
            result = await session.execute(
                select(InventoryItemRow).where(InventoryItemRow.sku == sku)
            )
            row = result.scalar_one()
            return _row_to_item(row)

    async def reserve(self, reservation: StockReservation) -> None:
        async with self._sf() as session:
            for item in reservation.items:
                row = ReservationRow(
                    reservation_id=reservation.id,
                    order_id=reservation.order_id,
                    sku=item.sku,
                    quantity_reserved=item.quantity_available,
                )
                session.add(row)
            await session.commit()

    async def release(self, reservation_id: UUID) -> None:
        async with self._sf() as session:
            result = await session.execute(
                select(ReservationRow).where(
                    ReservationRow.reservation_id == reservation_id
                )
            )
            rows = result.scalars().all()
            for row in rows:
                await session.delete(row)
            await session.commit()


def _row_to_item(row: InventoryItemRow) -> StockItem:
    return StockItem(
        id=row.id,  # type: ignore[arg-type]
        sku=row.sku,  # type: ignore[arg-type]
        quantity_available=row.quantity_available,  # type: ignore[arg-type]
    )
