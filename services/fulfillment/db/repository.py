from __future__ import annotations

from uuid import UUID

from fulfillment.domain.models import FulfillmentOrder


class FulfillmentRepository:
    async def save(self, fulfillment_order: FulfillmentOrder) -> None:
        raise NotImplementedError

    async def get(self, fulfillment_id: UUID) -> FulfillmentOrder:
        raise NotImplementedError

    async def update_status(self, fulfillment_id: UUID, status: str) -> None:
        raise NotImplementedError
