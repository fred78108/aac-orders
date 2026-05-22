from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from fulfillment.db.models import FulfillmentOrderRow
from fulfillment.domain.models import FulfillmentOrder, PackingStatus


class FulfillmentRepository:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        self._sf = session_factory

    async def save(self, fulfillment_order: FulfillmentOrder) -> None:
        async with self._sf() as session:
            row = FulfillmentOrderRow(
                id=fulfillment_order.id,
                order_id=fulfillment_order.order_id,
                items=fulfillment_order.items,
                status=fulfillment_order.status.value,
            )
            session.add(row)
            await session.commit()

    async def get(self, fulfillment_id: UUID) -> FulfillmentOrder:
        async with self._sf() as session:
            result = await session.execute(
                select(FulfillmentOrderRow).where(
                    FulfillmentOrderRow.id == fulfillment_id
                )
            )
            row = result.scalar_one()
            return _row_to_domain(row)

    async def get_by_order_id(self, order_id: UUID) -> FulfillmentOrder:
        async with self._sf() as session:
            result = await session.execute(
                select(FulfillmentOrderRow).where(
                    FulfillmentOrderRow.order_id == order_id
                )
            )
            row = result.scalar_one()
            return _row_to_domain(row)

    async def update_status(self, fulfillment_id: UUID, status: str) -> None:
        async with self._sf() as session:
            result = await session.execute(
                select(FulfillmentOrderRow).where(
                    FulfillmentOrderRow.id == fulfillment_id
                )
            )
            row = result.scalar_one()
            row.status = status  # type: ignore[assignment]
            await session.commit()


def _row_to_domain(row: FulfillmentOrderRow) -> FulfillmentOrder:
    return FulfillmentOrder(
        id=row.id,  # type: ignore[arg-type]
        order_id=row.order_id,  # type: ignore[arg-type]
        items=row.items or [],  # type: ignore[arg-type]
        status=PackingStatus(row.status),  # type: ignore[arg-type]
    )
