from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shipping.db.models import ShipmentRow
from shipping.domain.models import Shipment, ShipmentStatus


class ShipmentRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def save(self, shipment: Shipment) -> None:
        async with self._sf() as session:
            row = ShipmentRow(
                id=shipment.id,
                order_id=shipment.order_id,
                carrier=shipment.carrier,
                tracking_number=shipment.tracking_number,
                status=shipment.status.value,
            )
            session.add(row)
            await session.commit()

    async def get(self, shipment_id: UUID) -> Shipment:
        async with self._sf() as session:
            result = await session.execute(
                select(ShipmentRow).where(ShipmentRow.id == shipment_id)
            )
            row = result.scalar_one()
            return _row_to_domain(row)

    async def update_status(self, shipment_id: UUID, status: str) -> None:
        async with self._sf() as session:
            result = await session.execute(
                select(ShipmentRow).where(ShipmentRow.id == shipment_id)
            )
            row = result.scalar_one()
            row.status = status  # type: ignore[assignment]
            await session.commit()


def _row_to_domain(row: ShipmentRow) -> Shipment:
    return Shipment(
        id=row.id,  # type: ignore[arg-type]
        order_id=row.order_id,  # type: ignore[arg-type]
        carrier=row.carrier,  # type: ignore[arg-type]
        tracking_number=row.tracking_number,  # type: ignore[arg-type]
        status=ShipmentStatus(row.status),  # type: ignore[arg-type]
    )
