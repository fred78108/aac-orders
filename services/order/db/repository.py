from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from order.db.models import OrderItemRow, OrderRow
from order.domain.models import Order, OrderItem, OrderStatus


class OrderRepository:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        self._sf = session_factory

    async def save(self, order: Order) -> None:
        async with self._sf() as session:
            row = OrderRow(
                id=order.id,
                customer_id=order.customer_id,
                status=order.status.value,
                items=[
                    OrderItemRow(
                        sku=i.sku,
                        quantity=i.quantity,
                        unit_price_cents=i.unit_price_cents,
                    )
                    for i in order.items
                ],
            )
            session.add(row)
            await session.commit()

    async def get(self, order_id: UUID) -> Order:
        async with self._sf() as session:
            result = await session.execute(
                select(OrderRow)
                .options(selectinload(OrderRow.items))
                .where(OrderRow.id == order_id)
            )
            row = result.scalar_one()
            return Order(
                id=row.id,
                customer_id=row.customer_id,
                status=OrderStatus(row.status),
                items=[
                    OrderItem(
                        sku=i.sku,
                        quantity=i.quantity,
                        unit_price_cents=i.unit_price_cents,
                    )
                    for i in row.items
                ],
            )

    async def update_status(self, order_id: UUID, status: str) -> None:
        async with self._sf() as session:
            result = await session.execute(
                select(OrderRow).where(OrderRow.id == order_id)
            )
            row = result.scalar_one()
            row.status = status
            await session.commit()
