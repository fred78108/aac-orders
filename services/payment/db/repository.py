from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from payment.db.models import PaymentRow
from payment.domain.models import Payment, PaymentStatus


class PaymentRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def save(self, payment: Payment) -> None:
        async with self._sf() as session:
            row = PaymentRow(
                id=payment.id,
                order_id=payment.order_id,
                customer_id=payment.customer_id,
                amount_cents=payment.amount_cents,
                status=payment.status.value,
            )
            session.add(row)
            await session.commit()

    async def get(self, payment_id: UUID) -> Payment:
        async with self._sf() as session:
            result = await session.execute(
                select(PaymentRow).where(PaymentRow.id == payment_id)
            )
            row = result.scalar_one()
            return _row_to_domain(row)

    async def get_by_order_id(self, order_id: UUID) -> Payment:
        async with self._sf() as session:
            result = await session.execute(
                select(PaymentRow).where(PaymentRow.order_id == order_id)
            )
            row = result.scalar_one()
            return _row_to_domain(row)

    async def update_status(self, payment_id: UUID, status: str) -> None:
        async with self._sf() as session:
            result = await session.execute(
                select(PaymentRow).where(PaymentRow.id == payment_id)
            )
            row = result.scalar_one()
            row.status = status
            await session.commit()


def _row_to_domain(row: PaymentRow) -> Payment:
    return Payment(
        id=row.id,
        order_id=row.order_id,
        customer_id=row.customer_id,
        amount_cents=row.amount_cents,
        status=PaymentStatus(row.status),
    )
