from __future__ import annotations

from uuid import UUID

from payment.domain.models import Payment


class PaymentRepository:
    async def save(self, payment: Payment) -> None:
        raise NotImplementedError

    async def get(self, payment_id: UUID) -> Payment:
        raise NotImplementedError

    async def update_status(self, payment_id: UUID, status: str) -> None:
        raise NotImplementedError
